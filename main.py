from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import openai
import os
import base64
from sqlalchemy import create_engine, Column, String, Integer, Text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# 允許 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8001", "http://127.0.0.1:8001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 配置 OpenAI API
client = openai.OpenAI(api_key="")

# SQLite 數據庫
engine = create_engine("sqlite:///survey.db")
Base = declarative_base()

class Contact(Base):
    __tablename__ = "contacts"
    contact_id = Column(String, primary_key=True)
    phone_number = Column(String)

class Response(Base):
    __tablename__ = "responses"
    response_id = Column(String, primary_key=True)
    contact_id = Column(String)
    age = Column(Integer)
    occupation = Column(String)
    political_leaning = Column(String)
    response_text = Column(Text)
    timestamp = Column(String)

Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)

class CallRequest(BaseModel):
    contactId: str
    audio: str  # Base64 編碼音訊

# 預設議題和所需資訊
TOPIC = "施政滿意度"
REQUIRED_INFO = ["age", "occupation", "political_leaning"]
conversation_state = {"current_info": None, "collected_info": {}, "session_id": None}

@app.get("/api/contacts")
async def get_contacts():
    db = SessionLocal()
    contacts = db.query(Contact).all()
    db.close()
    return [{"id": c.contact_id, "phone_number": c.phone_number} for c in contacts]

@app.post("/api/initiate-call")
async def initiate_call(request: CallRequest):
    global conversation_state
    db = SessionLocal()

    # 解碼並保存音訊
    audio_data = base64.b64decode(request.audio.split(",")[1])
    with open("temp_audio.webm", "wb") as f:
        f.write(audio_data)

    # 使用 Whisper API 轉文字
    with open("temp_audio.webm", "rb") as audio_file:
        transcript_obj = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    transcript = transcript_obj.text

    # 初始化對話
    if not conversation_state["current_info"]:
        conversation_state["current_info"] = "start"
        conversation_state["collected_info"] = {}
        conversation_state["session_id"] = str(datetime.datetime.now().timestamp())

    # 處理對話流程
    if "不好" in transcript.lower():
        ai_response = "不好意思，感謝您的時間！"
        conversation_state["current_info"] = None
    else:
        if conversation_state["current_info"] == "start":
            messages = [
                {"role": "system", "content": f"你是一個調查代理，調查主題是'{TOPIC}'。以友好語氣問用戶是否願意參與調查。"},
                {"role": "user", "content": transcript}
            ]
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages
            )
            ai_response = response.choices[0].message.content
            if "好" in transcript.lower():
                conversation_state["current_info"] = REQUIRED_INFO[0]
        else:
            # 提取資訊並生成下一個問題
            messages = [
                {"role": "system", "content": f"你正在調查'{TOPIC}'，需收集{', '.join(REQUIRED_INFO)}。當前收集'{conversation_state['current_info']}'。從用戶回應提取信息，並生成一個簡潔友好的問題來收集下一個信息或繼續討論主題。用戶回應：{transcript}"},
                {"role": "user", "content": transcript}
            ]
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages
            )
            ai_response = response.choices[0].message.content

            # 提取結構化數據
            if conversation_state["current_info"] in REQUIRED_INFO:
                extract_messages = [
                    {"role": "system", "content": f"從以下文字提取{conversation_state['current_info']}：{transcript}"},
                    {"role": "user", "content": transcript}
                ]
                extract_response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=extract_messages
                )
                extracted = extract_response.choices[0].message.content
                if "age" in conversation_state["current_info"]:
                    try:
                        age = int(extracted.split("歲")[0].split()[-1]) if "歲" in extracted else None
                        conversation_state["collected_info"]["age"] = age
                    except:
                        pass
                elif "occupation" in conversation_state["current_info"]:
                    conversation_state["collected_info"]["occupation"] = extracted
                elif "political_leaning" in conversation_state["current_info"]:
                    conversation_state["collected_info"]["political_leaning"] = extracted

            # 移動到下一個資訊
            current_idx = REQUIRED_INFO.index(conversation_state["current_info"]) if conversation_state["current_info"] in REQUIRED_INFO else -1
            if current_idx + 1 < len(REQUIRED_INFO):
                conversation_state["current_info"] = REQUIRED_INFO[current_idx + 1]
            else:
                conversation_state["current_info"] = "topic_discussion"

    logger.info(f"Transcript: {transcript}, AI Response: {ai_response}")

    # 保存回應
    response_entry = Response(
        response_id=str(datetime.datetime.now().timestamp()),
        contact_id=request.contactId,
        age=conversation_state["collected_info"].get("age"),
        occupation=conversation_state["collected_info"].get("occupation"),
        political_leaning=conversation_state["collected_info"].get("political_leaning"),
        response_text=transcript + " | AI: " + ai_response,
        timestamp=str(datetime.datetime.now())
    )
    db.add(response_entry)
    db.commit()
    db.close()

    return {"response": ai_response}