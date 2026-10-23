"""Original code pasted by Cyrus in chat (2026-10-23) — from another AI.
Real working pattern: JSON-persisted memory + feedback-loop lesson learning via Gemini.
Kept as reference; the integrated version lives in brain/learning.py.
"""
import json
import os
from google import genai
from google.genai import types

class SuperMarketingAgent:
    def __init__(self, memory_file="bot_memory.json"):
        # فایل حافظه برای ذخیره تجربیات و اشتباهات
        self.memory_file = memory_file
        # مقداردهی API (کلید خود را در متغیر محیطی GEMINI_API_KEY قرار دهید)
        self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        self.memory = self.load_memory()

    def load_memory(self):
        # بارگذاری حافظه قبلی ربات
        if os.path.exists(self.memory_file):
            with open(self.memory_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"lessons_learned": [], "successful_campaigns": []}

    def save_memory(self):
        # ذخیره تجربیات جدید در فایل حافظه
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, ensure_ascii=False, indent=4)

    def generate_campaign(self, topic):
        # تزریق حافظه و اشتباهات گذشته به دستورات پایه ربات
        lessons = "\n- ".join(self.memory["lessons_learned"])

        system_instruction = f"""شما یک مدیر بازاریابی و استراتژیست شبکه‌های اجتماعی هستید.
        شما باید قبل از هر تصمیمی، اشتباهات گذشته خود را مرور کنید و آن‌ها را تکرار نکنید.

        درس‌هایی که از اشتباهات قبلی خود گرفته‌اید:
        - {lessons if lessons else 'شما به تازگی متولد شده‌اید و هنوز تجربه‌ای ندارید.'}
        """

        # درخواست از هوش مصنوعی با در نظر گرفتن حافظه
        response = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"یک پست جذاب شبکه‌های اجتماعی برای این موضوع بنویس: {topic}",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7
            )
        )
        return response.text

    def learn_from_feedback(self, post, feedback, is_positive):
        """
        بخش هوشمندی ربات: تحلیل اشتباهات و استخراج قوانین جدید
        """
        if is_positive:
            self.memory["successful_campaigns"].append(post)
            print("✅ کمپین موفق ارزیابی شد و در حافظه ثبت گردید.")
        else:
            # ربات دلیل شکست را تحلیل می‌کند و یک درس جدید می‌سازد
            analysis_prompt = f"""
            متن بازاریابی تولید شده: {post}
            انتقاد و بازخورد انسان/سیستم: {feedback}

            به عنوان یک هوش مصنوعی در حال یادگیری، در یک یا دو جمله کوتاه بگو دقیقاً چه قانونی باید برای خودت وضع کنی تا در آینده این اشتباه تکرار نشود؟
            """
            lesson_response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=analysis_prompt
            )
            new_lesson = lesson_response.text.strip()
            self.memory["lessons_learned"].append(new_lesson)
            print(f"🧠 درس جدید یاد گرفته شد: {new_lesson}")

        self.save_memory()

# --- نحوه استفاده توسط تیم شما ---
if __name__ == "__main__":
    bot = SuperMarketingAgent()

    # ۱. درخواست اول: ساخت یک پست برای تورهای تفریحی و طبیعت‌گردی
    topic = "تورهای تماشای حیات وحش و طبیعت‌گردی در جزیره ونکوور"
    print("در حال تولید محتوا بر اساس دانش فعلی...\n")
    draft = bot.generate_campaign(topic)
    print("--- پست پیشنهادی اول ---")
    print(draft)

    # ۲. ثبت خطای ربات (Feedback Loop)
    # فرض کنید ربات متن را خیلی طولانی نوشته و هشتگ‌های مناسب نزده است.
    human_feedback = "متن خیلی طولانی و خسته‌کننده بود. لحن باید ماجراجویانه‌تر باشد و در انتهای پست حتماً باید از هشتگ‌های پربازدید استفاده کنی."

    print("\n--- در حال پردازش بازخورد و یادگیری ---")
    bot.learn_from_feedback(draft, human_feedback, is_positive=False)

    # دفعه بعد که متد generate_campaign اجرا شود، ربات قانون جدید را در حافظه خود دارد
    # و به صورت خودکار پست‌های بعدی را کوتاه، ماجراجویانه و با هشتگ می‌نویسد.
