"""Second version pasted by Cyrus in chat (2026-10-23) — from another AI.
New vs v1: auto_critique_and_improve built-in, generate_and_save_image (Imagen 3),
InstagramHands (real Graph API two-step publish). __main__ truncated in paste.
cyrus's verdict: genuinely better, but image is saved LOCALLY while Instagram
needs a PUBLIC URL — missing upload bridge between the two.
Kept as reference; integrated versions live in robots/image_maker.py and
robots/instagram_publisher.py.
"""
import os
import json
import random
import datetime
import time
import requests
from google import genai
from google.genai import types

# ==========================================
# 🧠 بخش اول: مغز متفکر ربات (Agent)
# ==========================================
class SuperMarketingAgent:
    def __init__(self, memory_file="bot_memory.json"):
        self.memory_file = memory_file

        # خواندن کلید API جمنای از متغیرهای محیطی سیستم
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("❌ کلید API جمنای (GEMINI_API_KEY) یافت نشد!")

        self.client = genai.Client(api_key=api_key)
        self.memory = self.load_memory()

    def load_memory(self):
        if os.path.exists(self.memory_file):
            with open(self.memory_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"lessons_learned": [], "successful_campaigns": [], "replied_comments": []}

    def save_memory(self):
        with open(self.memory_file, "w", encoding="utf-8") as f:
            json.dump(self.memory, f, ensure_ascii=False, indent=4)

    def generate_campaign(self, topic):
        print(f"📝 در حال نوشتن پیش‌نویس درباره: {topic}")
        lessons = "\n- ".join(self.memory["lessons_learned"])

        system_instruction = f"""شما یک مدیر بازاریابی و استراتژیست شبکه‌های اجتماعی برای یک شرکت گردشگری و طبیعت‌گردی هستید.
        قبل از هر تصمیمی، اشتباهات گذشته خود را مرور کنید و آن‌ها را تکرار نکنید.

        درس‌هایی که از تجربه‌های قبلی خود گرفته‌اید:
        - {lessons if lessons else 'شما به تازگی متولد شده‌اید و هنوز تجربه‌ای ندارید.'}
        """

        response = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"یک پست بسیار جذاب برای اینستاگرام درباره این موضوع بنویس: {topic}. حتماً از ایموجی و هشتگ استفاده کن.",
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7
            )
        )
        return response.text

    def auto_critique_and_improve(self, topic, draft):
        print("🕵️ در حال ارزیابی و اصلاح متن توسط منتقد هوش مصنوعی...")
        critic_instruction = """شما یک مدیر ارشد بازاریابی سخت‌گیر هستید. بررسی کنید:
        - آیا قلاب (Hook) اولیه جذاب است؟
        - آیا متن برای اینستاگرام مناسب است و طولانی نیست؟
        - آیا کال تو اکشن (Call to Action) شفاف است؟
        فقط ایرادات را تیتروار بنویس. اگر متن عالی است، فقط بنویس: "تایید شد".
        """

        critique_response = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"موضوع: {topic}\n\nپیش‌نویس:\n{draft}",
            config=types.GenerateContentConfig(
                system_instruction=critic_instruction,
                temperature=0.3
            )
        )

        critique = critique_response.text.strip()
        if "تایید شد" in critique:
            print("✅ متن توسط منتقد تایید شد.")
            return draft

        print("✍️ در حال بازنویسی بر اساس نقدهای منتقد...")
        rewrite_prompt = f"متن اولیه:\n{draft}\n\nایرادات منتقد:\n{critique}\n\nبا دقت به این نقدها، یک نسخه نهایی و بی‌نقص برای اینستاگرام بنویس. فقط متن نهایی را برگردان."

        final_response = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=rewrite_prompt,
            config=types.GenerateContentConfig(temperature=0.7)
        )
        return final_response.text

    def generate_and_save_image(self, final_post, output_path="temp_image.png"):
        print("🎨 در حال طراحی سناریوی تصویر بر اساس متن پست...")
        prompt_generator = self.client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"Based on this instagram post, write a highly detailed, photorealistic, cinematic prompt in English for an AI image generator. The image should be vibrant, natural, and perfect for an outdoor adventure Instagram page. Return ONLY the english prompt:\n\n{final_post}"
        )
        image_prompt = prompt_generator.text.strip()
        print(f"👁️ دستور تولید تصویر: {image_prompt}")

        print("📸 در حال ساخت تصویر با Imagen 3...")
        result = self.client.models.generate_images(
            model='imagen-3.0-generate-002',
            prompt=image_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/png",
                aspect_ratio="1:1"
            )
        )

        for generated_image in result.generated_images:
            generated_image.image.save(output_path)
            print(f"💾 تصویر در '{output_path}' ذخیره شد.")
            return output_path
        return None

# ==========================================
# 📱 بخش دوم: دست‌های اینستاگرامی (Instagram API)
# ==========================================
class InstagramHands:
    def __init__(self, ig_user_id):
        self.access_token = os.environ.get("IG_ACCESS_TOKEN")
        self.ig_user_id = ig_user_id
        self.base_url = "https://graph.facebook.com/v18.0"

        if not self.access_token:
            print("⚠️ هشدار: توکن اینستاگرام (IG_ACCESS_TOKEN) یافت نشد.")

    def publish_post(self, image_url, caption):
        """آپلود عکس و انتشار پست در اینستاگرام"""
        print("📱 در حال ارتباط با سرورهای متا برای انتشار پست...")

        # ۱. ساخت کانتینر در سرور
        media_url = f"{self.base_url}/{self.ig_user_id}/media"
        media_payload = {
            'image_url': image_url,
            'caption': caption,
            'access_token': self.access_token
        }

        media_response = requests.post(media_url, data=media_payload).json()

        if 'id' not in media_response:
            print("❌ خطا در مرحله اول آپلود:", media_response)
            return False

        creation_id = media_response['id']
        print("⏳ عکس با موفقیت در متا بارگذاری شد. ۵ ثانیه استراحت تا پردازش سرور...")
        time.sleep(5) # صبر برای پردازش عکس توسط اینستاگرام

        # ۲. انتشار نهایی
        publish_url = f"{self.base_url}/{self.ig_user_id}/media_publish"
        publish_payload = {
            'creation_id': creation_id,
            'access_token': self.access_token
        }

        publish_response = requests.post(publish_url, data=publish_payload).json()

        if 'id' in publish_response:
            print(f"🎉 تبریک! پست با موفقیت در اینستاگرام منتشر شد. کد پست: {publish_response['id']}")
            return True
        else:
            print("❌ خطا در انتشار نهایی:", publish_response)
            return False

# ==========================================
# 🚀 بخش سوم: اجرای کامل و خودکار برنامه
# ==========================================
# NOTE: __main__ was truncated in the chat paste — execution part missing.
