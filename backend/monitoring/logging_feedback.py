import logging
from fastapi import FastAPI, Request

# Setup logging
logging.basicConfig(
    filename="/app/logs/system.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

app = FastAPI()


@app.post("/feedback")
async def feedback(request: Request):
    data = await request.json()
    logging.info(f"Feedback received: {data}")
    return {"status": "success", "received_feedback": data}


logging.info("Continuous monitoring and feedback system initialized.")
