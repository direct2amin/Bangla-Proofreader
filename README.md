# 🇧🇩 বাংলা প্রুফরিডার (Bangla Proofreader) — v1.4.0

> **AI-Powered Windows Desktop Utility for Bangla Proofreading, Bijoy-to-Unicode Conversion & Linguistic Correction**  
> সিস্টেম-ওয়াইড গ্লোবাল শর্টকাট, অটোমেটিক বিজয়-টু-ইউনিকোড কনভার্টার, আরবি স্ক্রিপ্ট প্রোটেকশন এবং Google Gemini AI সমর্থিত আধুনিক বাংলা প্রুফরিডার।

---

## 📥 ডাউনলোড ও ইনস্টলেশন (Download for Windows)

সোর্স কোড ছাড়া সরাসরি উইন্ডোজে ব্যবহার করতে চাইলে এই রিপোজিটরির **[Releases](../../releases)** সেকশন থেকে সর্বশেষ **`BanglaProofreader_Setup_v1.4.0.exe`** ইনস্টলারটি ডাউনলোড করে ইনস্টল করুন।

---

## ✨ মূল বৈশিষ্ট্যসমূহ (Key Features)

- **⚡ সিস্টেম-ওয়াইড গ্লোবাল শর্টকাট (Global Hotkey):** যেকোনো অ্যাপ্লিকেশন (Microsoft Word, Adobe Illustrator, Notepad, Browser) থেকে লেখা সিলেক্ট করে `Ctrl+Alt+B` (অথবা সেটিংস থেকে আপনার পছন্দমতো কাস্টম শর্টকাট) চাপলেই সরাসরি প্রুফরিডার চালু হয়।
- **🔄 অটোমেটিক বিজয়-টু-ইউনিকোড কনভার্সন (Auto Bijoy-to-Unicode):** বিজয় (SutonnyMJ/ANSI) ফন্টের লেখা কপি বা পেস্ট করলে স্বয়ংক্রিয়ভাবে ইউনিকোডে রূপান্তর করে প্রুফরিড সম্পন্ন করে।
- **🕋 আরবি টেক্সট ও হরকত সুরক্ষা (Arabic Script Protection):** বাংলা লেখার ভেতরে কুরআনের আয়াত, হাদিস বা আরবি দোয়া থাকলে তার অক্ষর ও হরকত ১০০% অক্ষুণ্ণ রাখে।
- **📍 বাংলাদেশের স্থাননাম অভিধান (BD Location Gazetteer):** বাংলাদেশের জেলা, উপজেলা, থানা, ইউনিয়ন ও পোস্ট অফিসের নামের বানান নির্ভুলভাবে যাচাই ও সংশোধন করে।
- **🎨 পাশাপাশি ও ইনলাইন তুলনা (Visual Word-Level Diff):**
  - বাম পাশে মূল লেখার ভুল শব্দগুলো **লাল হাইলাইট** এবং ডান পাশে শুদ্ধ রূপটি **সবুজ হাইলাইট** সহ প্রদর্শন।
  - দুই পাশের লাইন স্পেসিং ও স্ক্রলিং শতভাগ সিঙ্ক্রোনাইজড।
  - বিদেশি বা ইংরেজি প্রতিবর্ণীকৃত শব্দগুলো **হলুদ ব্যাজ** সহ নিচে এবং স্ট্রাইকথ্রু ছাড়া আলাদাভাবে চিহ্নিত করে।
- **🖌️ Adobe Illustrator ও Active App সাপোর্ট:** **"Replace in Active App"** বাটনে ক্লিক করলে সরাসরি আগের অ্যাপে শুদ্ধ লেখা পেস্ট হয় এবং Adobe Illustrator-এ মাত্র **১ বার `Ctrl+Z`** চাপলেই আনডো (Undo) করা যায়।
- **🌗 থিম ও ইউজার ইন্টারফেস:** **Light Mode**, **Dark Mode** ও **System Default** থিম এবং বাংলা ও ইংরেজি উভয় ভাষায় ইন্টারফেস পরিবর্তনের সুবিধা।

---

## 📁 প্রোজেক্ট স্ট্রাকচার (Project Structure)

```text
Bangla-Proofreader/
├── app/
│   ├── main.py                        # অ্যাপ্লিকেশন এন্ট্রি পয়েন্ট ও সিস্টেম ট্রে ইন্টিগ্রেশন
│   ├── assets/                        # অ্যাপ আইকন ও বাংলাদেশের স্থাননাম ডেটাবেস (bd_locations.json)
│   ├── core/
│   │   ├── clipboard.py               # উইন্ডোজ ক্লিপবোর্ড ক্যাপচার ও সিঙ্গেল-স্টেপ পেস্ট ইনজেকশন
│   │   ├── config.py                  # %APPDATA% কনফিগারেশন ম্যানেজার
│   │   ├── engine_manager.py          # প্রুফরিডিং ইঞ্জিন রাউটার
│   │   ├── shortcuts.py               # Win32 গ্লোবাল হটকি লিসেনার
│   │   └── theme.py                   # Light/Dark/System থিম ও Win32 DWM টাইটেল বার স্টাইলিং
│   ├── engines/
│   │   └── gemini_engine.py           # Google Gemini AI প্রুফরিডিং ইঞ্জিন ও প্রম্পট গার্ড
│   ├── ui/
│   │   ├── diff_window.py             # মেইন প্রুফরিডার ও সাইড-বাই-সাইড ডিফ উইন্ডো
│   │   ├── settings_dialog.py         # সেটিংস ও কাস্টম শর্টকাট ডায়ালগ
│   │   ├── api_guide_dialog.py        # ফ্রি Gemini API Key নেওয়ার গাইড উইন্ডো
│   │   └── about_dialog.py            # ডেভেলপার পরিচিতি ও ভার্সন তথ্য
│   └── utils/
│       ├── bijoy_converter.py         # বিজয় (ANSI) থেকে ইউনিকোড কনভার্টার ও আরবি মাস্কিং
│       ├── bd_gazetteer.py            # বাংলাদেশের স্থাননাম ফাজি ম্যাচিং ইউটিলিটি
│       ├── diff_highlighter.py        # শব্দভিত্তিক ডিফ ক্যালকুলেশন
│       ├── foreign_words.py           # বিদেশি শব্দ শনাক্তকরণ ও দেশীয় প্রতিশব্দ সাজেশন
│       ├── punctuation_formatter.py   # বাংলা যতিচিহ্ন ও স্পেসিং ফরম্যাটার
│       ├── autostart.py               # উইন্ডোজ স্টার্টআপ রেজিস্ট্রি ইন্টিগ্রেশন
│       └── i18n.py                    # দ্বিভাষিক (বাংলা/ইংরেজি) অনুবাদ ডিকশনারি
├── tests/                             # ইউনিট টেস্ট স্যুট
├── BanglaProofreader.spec             # PyInstaller বিল্ড স্পেসিফিকেশন
├── installer.iss                      # Inno Setup ইনস্টলার স্ক্রিপ্ট
├── config.example.json                # কনফিগারেশন ফাইলের নমুনা
├── requirements.txt                   # পাইথন ডিপেন্ডেন্সি তালিকা
├── CHANGELOG.txt                      # ভার্সন পরিবর্তনের বিস্তারিত ইতিহাস
└── LICENSE                            # MIT ওপেন-সোর্স লাইসেন্স
```

---

## 🛠️ সোর্স কোড থেকে রান করার নিয়ম (Run from Source)

### ১. রিপোজিটরি ক্লোন করুন
```powershell
git clone https://github.com/direct2amin/bangla-proofreader.git
cd bangla-proofreader
```

### ২. ডিপেন্ডেন্সি ইনস্টল করুন
```powershell
pip install -r requirements.txt
```

### ৩. অ্যাপ্লিকেশন রান করুন
```powershell
python -m app.main
```

### ৪. ইউনিট টেস্ট রান করুন
```powershell
python -m unittest discover -s tests -p "test_*.py"
```

---

## 📦 ইনস্টলার (.exe) বিল্ড করার নিয়ম (Build Standalone Installer)

১. **PyInstaller দিয়ে অ্যাপ বান্ডেল তৈরি:**
```powershell
pyinstaller BanglaProofreader.spec --noconfirm
```
২. **Inno Setup দিয়ে `BanglaProofreader_Setup.exe` তৈরি:**
```powershell
iscc installer.iss
```

---

## 👨‍💻 ডেভেলপার (Developer)

- **Developed by:** Amin
- **Portfolio:** [https://direct2amin.github.io/aminsweb/](https://direct2amin.github.io/aminsweb/)
- **License:** [MIT License](LICENSE)
