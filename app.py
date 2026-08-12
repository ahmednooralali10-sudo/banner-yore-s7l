from io import BytesIO
import aiohttp
import asyncio
from flask import Flask, Response, jsonify
from PIL import Image, ImageDraw, ImageFont

try:
  import arabic_reshaper
  from bidi.algorithm import get_display

  HAS_ARABIC_SUPPORT = True
except ImportError:
  HAS_ARABIC_SUPPORT = False

app = Flask(__name__)


async def fetch_data_and_images(uid: str):
  api_url = f"https://api-info-alliff-d5m.vercel.app/info={uid}"

  async with aiohttp.ClientSession() as session:
    async with session.get(api_url) as resp:
      if resp.status != 200:
        return None, "فشل الاتصال بالـ API أو الايدي غير صحيح"
      data = await resp.json()

    try:
      basic_info = data.get("basicInfo", {})
      banner_id = basic_info.get("bannerId")
      head_pic = basic_info.get("headPic")
      nickname = data.get("nickname", "Unknown")
      level = data.get("level", "N/A")

      if not banner_id or not head_pic:
        return None, "لم يتم العثور على بيانات البانر أو الأفاتار"

      banner_url = (
          f"https://star-icon-png.lovable.app/png?icon_id={banner_id}"
      )
      headpic_url = f"https://star-icon-png.lovable.app/png?icon_id={head_pic}"

      async with session.get(banner_url) as b_resp, session.get(
          headpic_url
      ) as h_resp:
        if b_resp.status != 200 or h_resp.status != 200:
          return None, "فشل في تحميل صور الايقونات"

        banner_bytes = await b_resp.read()
        headpic_bytes = await h_resp.read()

        return (
            banner_bytes,
            headpic_bytes,
            nickname,
            str(level),
        ), None

    except Exception as e:
      return None, f"حدث خطأ أثناء معالجة البيانات: {str(e)}"


@app.route("/banner/<uid>", methods=["GET"])
def get_banner(uid):
  loop = asyncio.new_event_loop()
  asyncio.set_event_loop(loop)
  result, error = loop.run_until_complete(fetch_data_and_images(uid))
  loop.close()

  if error:
    return jsonify({"error": error}), 400

  banner_bytes, headpic_bytes, nickname, level = result

  try:
    img_head = Image.open(BytesIO(headpic_bytes)).convert("RGBA")
    img_banner = Image.open(BytesIO(banner_bytes)).convert("RGBA")

    hw, hh = img_head.size
    bw, bh = img_banner.size

    padding_x = 20
    padding_y = 15
    top_bar_height = 30
    text_space = 35
    spacing = 15

    total_width = hw + bw + spacing + (padding_x * 2)
    max_img_height = max(hh, bh)
    total_height = top_bar_height + max_img_height + text_space + (padding_y * 2)

    background_color = (20, 20, 25, 255)
    combined_img = Image.new(
        "RGBA", (total_width, total_height), background_color
    )

    draw = ImageDraw.Draw(combined_img)

    try:
      font_title = ImageFont.truetype("arial.ttf", 16)
      font_text = ImageFont.truetype("arial.ttf", 15)
    except:
      font_title = ImageFont.load_default()
      font_text = ImageFont.load_default()

    # 1. الحقوق في الأعلى
    watermark_text = "S7L - YORE TEam"
    bbox_wm = draw.textbbox((0, 0), watermark_text, font=font_title)
    wm_width = bbox_wm[2] - bbox_wm[0]
    wm_x = (total_width - wm_width) // 2
    wm_y = 8
    draw.text(
        (wm_x, wm_y), watermark_text, fill=(230, 60, 60, 255), font=font_title
    )

    # 2. إحداثيات الصور
    start_y = top_bar_height + padding_y

    head_x = padding_x
    head_y = start_y + (max_img_height - hh) // 2

    banner_x = padding_x + hw + spacing
    banner_y = start_y + (max_img_height - bh) // 2

    combined_img.paste(img_head, (head_x, head_y), img_head)
    combined_img.paste(img_banner, (banner_x, banner_y), img_banner)

    def fix_arabic(text):
      if HAS_ARABIC_SUPPORT:
        reshaped_text = arabic_reshaper.reshape(text)
        return get_display(reshaped_text)
      return text

    # 3. النصوص في الأسفل
    text_y = start_y + max_img_height + 8

    level_text = f"Level: {level}"
    bbox_lvl = draw.textbbox((0, 0), level_text, font=font_text)
    lvl_w = bbox_lvl[2] - bbox_lvl[0]
    lvl_x = head_x + (hw - lvl_w) // 2
    draw.text(
        (lvl_x, text_y), level_text, fill=(200, 200, 200, 255), font=font_text
    )

    fixed_nickname = fix_arabic(nickname)
    bbox_nick = draw.textbbox((0, 0), fixed_nickname, font=font_text)
    nick_w = bbox_nick[2] - bbox_nick[0]
    nick_x = banner_x + (bw - nick_w) // 2
    draw.text(
        (nick_x, text_y),
        fixed_nickname,
        fill=(255, 255, 255, 255),
        font=font_text,
    )

    output_buffer = BytesIO()
    combined_img.save(output_buffer, format="PNG")
    output_buffer.seek(0)

    return Response(output_buffer.getvalue(), mimetype="image/png")

  except Exception as e:
    return jsonify({"error": f"حدث خطأ أثناء معالجة الصور: {str(e)}"}), 500

