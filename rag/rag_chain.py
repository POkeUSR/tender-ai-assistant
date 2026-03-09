from langchain_openai import ChatOpenAI
from rag.prompt import tender_prompt


def ask_llm(vectorstore, question):

    docs = vectorstore.similarity_search(question, k=4)

    context = ""

    for doc in docs:
        if hasattr(doc, "page_content"):
            context += doc.page_content + "\n"
        else:
            context += str(doc) + "\n"

    prompt = tender_prompt.format(
        context=context,
        question=question
    )

    llm = ChatOpenAI(model="gpt-4o-mini")

    response = llm.invoke(prompt)

    return response.content