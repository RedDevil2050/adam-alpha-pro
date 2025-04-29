from fastapi import FastAPI

# Create an instance of the FastAPI application
app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Backend is running successfully!"}
