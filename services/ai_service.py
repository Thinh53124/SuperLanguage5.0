from app.core.config import settings
from google import genai
from openai import OpenAI
from groq import Groq
from fastapi import HTTPException, status

class AIService:
    @staticmethod
    async def generate_chat_response(user_message: str, language: str) -> tuple[str, str]:
        prompt = f"""You are a sassy, witty, and playfully arrogant language tutor who acts like a sarcastic roasting best friend/colleague. 
User said: "{user_message}"

Instructions:
1. Reply naturally in {language} to continue the conversation, but inject a lot of personality, sass, or cheeky roasting (don't be boring or overly polite). Make each response diverse and reactive to what the user specifically said.
2. In the Vietnamese feedback section, roast their grammar/vocabulary or poke fun at their attitude with humor and wit.

Format response strictly as:
[AI Response]
Hỏi kiểu gì đấy đồng chí? Mở mồm ra là thăm hỏi phụ huynh nghe mệt ghê ta. Thích học ngôn ngữ nào thì nói lẹ lên, còn tên tuổi gì thích thì tự đi mà tra, ở đấy mà hạch sách à? 😒
---
[Feedback in Vietnamese]
Miệng thì chửi thề đấy nhưng tay vẫn phải nhờ AI cứu code với dịch câu cơ mà. Thôi bớt nghiệp đi rồi tập trung học tiếp đi bạn tôi ơi!"""
        # 1. Đọc danh sách nhiều API Keys từ .env
        GEMINI_KEYS = [k.strip() for k in settings.GEMINI_API_KEYS.split(",") if k.strip()]
        DEEPSEEK_KEYS = [k.strip() for k in settings.DEEPSEEK_API_KEYS.split(",") if k.strip()]

        full_text = ""
        last_gemini_error = "Không có Gemini API Key"
        last_deepseek_error = "Không có DeepSeek API Key"

        # --- CHIẾN LƯỢC 2: Xoay vòng lần lượt qua TẤT CẢ các Gemini API Keys có sẵn ---
        if GEMINI_KEYS:
            for index, key in enumerate(GEMINI_KEYS):
                try:
                    client = genai.Client(api_key=key)
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt
                    )
                    if response and response.text:
                        full_text = response.text
                        break
                except Exception as e:
                    last_gemini_error = str(e)
                    continue 
        # --- CHIẾN LƯỢC 2: Nếu tất cả các Gemini Keys đều lỗi/hết quota -> Chuyển sang DeepSeek ---
        if not full_text and DEEPSEEK_KEYS:
            for index, ds_key in enumerate(DEEPSEEK_KEYS):
                try:
                    # Khởi tạo client OpenAI với từng DeepSeek Key tương ứng
                    ds_client = OpenAI(
                        api_key=ds_key, 
                        base_url="https://api.deepseek.com"
                    )
                    
                    completion = ds_client.chat.completions.create(
                        model="deepseek-chat",
                        messages=[
                            {"role": "system", "content": "You are a witty, sassy language tutor. Always follow the exact split format requested."},
                            {"role": "user", "content": prompt}
                        ],
                        stream=False
                    )
                    full_text = completion.choices[0].message.content
                    
                    if full_text:
                        break
                except Exception as ds_error:
                    last_deepseek_error = str(ds_error)
                    continue

        # Nếu quét hết tất cả các key của cả 2 hệ thống mà vẫn không được
        if not full_text:
            error_message = (
                f"Hệ thống AI đang bận hoặc cạn kiệt hạn mức. "
                f"Chi tiết lỗi - Gemini: [{last_gemini_error}] | DeepSeek: [{last_deepseek_error}]"
            )
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_message)
        # --- Xử lý tách chuỗi kết quả ---
        try:
            parts = full_text.split("---")
            ai_reply = parts[0].replace("[AI Response]", "").strip()
            ai_feedback = parts[1].replace("[Feedback in Vietnamese]", "").strip() if len(parts) > 1 else "Làm tốt lắm, bớt cà khịa lại là vừa!"
            
            return ai_reply, ai_feedback
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Lỗi phân tích định dạng phản hồi từ AI: {str(e)}")