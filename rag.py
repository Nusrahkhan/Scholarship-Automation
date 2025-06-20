# SUNO BHAI BEHNO, ye please install kar lo:
# pip install google-generativeai langchain-google-genai langchain langchain-community chromadb faiss-cpu sentence-transformers pypdf

import google.generativeai as genai
from langchain_google_genai import GoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

api_key = 'AIzaSyAesqyliwOM5cGUKejbfLLTewG28ckIDgM'
genai.configure(api_key=api_key)

llm = GoogleGenerativeAI(model="gemini-2.0-flash",
                        google_api_key=api_key,
                        temperature=0.3)

def process_pdf(pdf_path):
    """
    Load and process a PDF file, splitting it into chunks for better processing
    """
    # Load PDF
    loader = PyPDFLoader(pdf_path)
    pages = loader.load()

class PDFQuestionAnswering:
    def __init__(self, api_key):
        self.api_key = api_key
        genai.configure(api_key=api_key)

        # Initialize Gemini model
        self.llm = GoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=api_key,
            temperature=0.1
        )

        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=api_key
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
            length_function=len
        )

    def load_pdf(self, pdf_path):
        """Load PDF and split into chunks"""
        try:
            # Load PDF
            loader = PyPDFLoader(pdf_path)
            pages = loader.load()

            # Split pages into chunks
            chunks = self.text_splitter.split_documents(pages)
            print(f"Successfully split PDF into {len(chunks)} chunks")

            # Create vector store
            self.vectordb = FAISS.from_documents(chunks, self.embeddings)
            self.retriever = self.vectordb.as_retriever(search_kwargs={"k": 3})

            # Create QA chain
            prompt_template = """Use the following context to answer the question.
            If the answer cannot be found in the context, say "I don't know."
            Try to be as detailed as possible while staying true to the context.

            Context: {context}

            Question: {question}

            Answer:"""

            PROMPT = PromptTemplate(
                template=prompt_template,
                input_variables=["context", "question"]
            )

            self.qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=self.retriever,
                return_source_documents=True,
                chain_type_kwargs={"prompt": PROMPT}
            )

            return True

        except Exception as e:
            print(f"Error loading PDF: {str(e)}")
            return False

    def ask_question(self, question):
        """Ask a question about the loaded PDF"""
        if not hasattr(self, 'qa_chain'):
            print("Please load a PDF first!")
            return

        try:
            result = self.qa_chain.invoke({"query": question})

            print("\n🤖 Answer:")
            print(result["result"])

        except Exception as e:
            print(f"Error processing question: {str(e)}")

def main():
    # Initialize the system
    pdf_qa = PDFQuestionAnswering(api_key)

    # Load your PDF
    pdf_path = r"C:\Users\saria\OneDrive\Desktop\AWS WEBSITE\Scholarship-Automation\Scholarship rag.pdf"  #meow, ek baar path check karlena
    if pdf_qa.load_pdf(pdf_path):
        print("\n✅ PDF loaded successfully! You can now ask questions.")

        # Interactive questioning loop
        while True:
            question = input("\n❓ Enter your question (or 'quit' to exit): ")
            if question.lower() in ['quit', 'exit', 'q']:
                break

            pdf_qa.ask_question(question)
    else:
        print("Failed to load PDF. Please check the file path and try again.")

if __name__ == "__main__":
    main()