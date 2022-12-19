from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, BaseSettings
from typing import List
from top2vec import Top2Vec
import uvicorn
import numpy as np

class Settings(BaseSettings):
    model_name: str = "Datawise NLP API"
    model_path: str = "models/top2vec_model_best"

settings = Settings()

model = Top2Vec.load(settings.model_path)

app = FastAPI(title=settings.model_name,
             description="Restful NLP API",
             version="1.0.0",)

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=404,
        content={"message": str(exc)},
    )

# Determine top2vec index type
#if model.document_ids is np.str_:
#    doc_id_type = str
#else:
#    doc_id_type = int
doc_id_type = str

# Determine if model has documents
if model.documents is None:
    has_documents = False
else:
    has_documents = True

class Document(BaseModel):
    if has_documents:
        content: str
    score: float
    doc_id: doc_id_type

class DocumentSearch(BaseModel):
    doc_ids: List[doc_id_type]
    doc_ids_neg: List[doc_id_type]
    num_docs: int

class NumTopics(BaseModel):
    num_topics: int

class TopicSizes(BaseModel):
    topic_nums: List[int]
    topic_sizes: List[int]

class Topic(BaseModel):
    topic_num: int
    topic_words: List[str]
    word_scores: List[float]

class TopicResult(Topic):
    topic_score: float

class KerwordSearch(BaseModel):
    keywords: List[str]
    keywords_neg: List[str]

class KeywordSearchDocument(KerwordSearch):
    num_docs: int

class KeywordSearchTopic(KerwordSearch):
    num_topics: int

class KeywordSearchWord(KerwordSearch):
    num_words: int

class WordResult(BaseModel):
    word: str
    score: float

@app.get('/')
@app.get('/home')
def read_home():
    """Home endpoint which can be used to test application availability."""
    return {'message': 'System is healthy. Go to /docs to interact with endpoints'}

@app.get("/topics/number", response_model=NumTopics, description="Returns number of topics in the model.",
         tags=["Topics"])
async def get_number_of_topics():
    return NumTopics(num_topics=model.get_num_topics())

@app.get("/topics/sizes", response_model=TopicSizes, description="Returns the number of documents in each topic.",
         tags=["Topics"])
async def get_topic_sizes():
    topic_sizes, topic_nums = model.get_topic_sizes()
    return TopicSizes(topic_nums=list(topic_nums), topic_sizes=list(topic_sizes))

@app.get("/topics/get-topics", response_model=List[Topic], description="Get number of topics.", tags=["Topics"])
async def get_topics(num_topics: int):
    topic_words, word_scores, topic_nums = model.get_topics(num_topics)

    topics = []
    for words, scores, num in zip(topic_words, word_scores, topic_nums):
        topics.append(Topic(topic_num=num, topic_words=list(words), word_scores=list(scores)))

    return topics

@app.post("/topics/search", response_model=List[TopicResult], description="Semantic search of topics using keywords.",
          tags=["Topics"])
async def search_topics_by_keywords(keyword_search: KeywordSearchTopic):
    topic_words, word_scores, topic_scores, topic_nums = model.search_topics(keyword_search.keywords,
                                                                               keyword_search.num_topics,
                                                                               keyword_search.keywords_neg)

    topic_results = []
    for words, word_scores, topic_score, topic_num in zip(topic_words, word_scores, topic_scores, topic_nums):
        topic_results.append(TopicResult(topic_num=topic_num, topic_words=list(words),
                                         word_scores=list(word_scores), topic_score=topic_score))

    return topic_results

@app.get("/documents/search-by-topic", response_model=List[Document],
         description="Semantic search of documents using keywords.", tags=["Documents"])
async def search_documents_by_topic(topic_num: int, num_docs: int):
    documents = []

    if has_documents:
        docs, doc_scores, doc_ids = model.search_documents_by_topic(topic_num, num_docs)
        for doc, score, num in zip(docs, doc_scores, doc_ids):
            documents.append(Document(content=doc, score=score, doc_id=num))

    else:
        doc_scores, doc_ids = model.search_documents_by_topic(topic_num, num_docs)
        for score, num in zip(doc_scores, doc_ids):
            documents.append(Document(score=score, doc_id=num))

    return documents

@app.post("/documents/search-by-documents", response_model=List[Document], description="Find similar documents.",
          tags=["Documents"])
async def search_documents_by_documents(document_search: DocumentSearch):
    documents = []

    if has_documents:
        docs, doc_scores, doc_ids = model.search_documents_by_documents(document_search.doc_ids,
                                                                          document_search.num_docs,
                                                                          document_search.doc_ids_neg)
        for doc, score, num in zip(docs, doc_scores, doc_ids):
            documents.append(Document(content=doc, score=score, doc_id=num))
    else:
        doc_scores, doc_ids = model.search_documents_by_documents(document_search.doc_ids,
                                                                    document_search.num_docs,
                                                                    document_search.doc_ids_neg)
        for score, num in zip(doc_scores, doc_ids):
            documents.append(Document(score=score, doc_id=num))

    return documents

@app.post("/words/find-similar", response_model=List[WordResult], description="Search documents by keywords.",
          tags=["Words"])
async def find_similar_words(keyword_search: KeywordSearchWord):
    words, word_scores = model.similar_words(keyword_search.keywords, keyword_search.num_words,
                                               keyword_search.keywords_neg)

    word_results = []
    for word, score in zip(words, word_scores):
        word_results.append(WordResult(word=word, score=score))

    return word_results

if __name__ == '__main__':
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)