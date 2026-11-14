# Introduction to RAG

## 1. What is RAG?

RAG stands for **Retrieval-Augmented Generation**.

It is a technique that helps an AI system find useful information before answering a question.

Think of it like an open-book exam. Instead of answering only from memory, you can look at your textbook and use the information to give a better answer.

RAG works in a similar way:
- It searches for relevant information.
- It gives that information to an AI language model.
- The model uses it to generate an answer.

## 2. Why is RAG useful?

Large Language Models (LLMs) learn from training data. However, they may not know new information or details from private documents.

RAG helps by allowing an AI system to use information from external sources, such as PDFs, company documents, and knowledge bases.

Benefits include:
- Answers based on relevant documents.
- Access to information that was not part of the model's training.
- Less chance of making up information when retrieval and generation work correctly.
- No need to retrain the entire language model whenever documents change.

RAG does not guarantee correct answers. The quality of the retrieved information still matters.

## 3. How does RAG work?

A basic RAG system follows four steps:

1. **User asks a question:** For example, "What is the company's leave policy?"
2. **Retrieve information:** The system searches its document collection for relevant sections.
3. **Provide context:** The retrieved information is given to the Large Language Model (LLM), along with the question.
4. **Generate an answer:** The LLM uses the question and retrieved information to create a response.

In simple terms:

**Question → Retrieve → Add context → Generate answer**

## 4. Practical example

Imagine a college has a PDF containing its attendance policy.

A student asks:

"What is the minimum attendance required for exams?"

Without RAG, a general AI model might not know that college's specific rule.

With RAG:
1. The system searches the college PDF.
2. It finds the section about attendance.
3. It provides that section to the LLM.
4. The LLM explains the attendance requirement to the student.

The answer is based on the college document rather than a guess.

## 5. What are embeddings?

Embeddings are lists of numbers that represent the meaning of text.

For example, the sentences:
- "How can I reset my password?"
- "I forgot my login password."

They use different words but have similar meanings.

An embedding model converts text into numbers so that a computer can compare their meaning.

## 6. What is vector search?

Vector search finds information by comparing embeddings.

It helps a RAG system find text that is similar in meaning to a user's question, even when the exact words are different.

For example, searching for "reset password" may retrieve a document containing "forgot login password."

A vector database can store these embeddings and help retrieve relevant information efficiently.

## 7. RAG vs. a normal LLM answer

| Normal LLM | LLM with RAG |
|---|---|
| Answers mainly using learned knowledge. | Uses learned knowledge and retrieved information. |
| May not know private documents. | Can search connected private documents. |
| May lack recent information. | Can use updated information available in its document collection. |
| Can produce unsupported answers. | Retrieved context can help ground answers. |

Both approaches can make mistakes. RAG improves access to relevant information but does not guarantee accuracy.

## 8. Quick recap

- RAG means Retrieval-Augmented Generation.
- It helps an AI system find information before generating an answer.
- It retrieves relevant content and provides it to an LLM as context.
- Embeddings represent the meaning of text as numbers.
- Vector search finds text with similar meaning.
- RAG is useful for answering questions about documents and other external information.

**Remember:** RAG gives an AI model useful information to refer to before it answers a question.