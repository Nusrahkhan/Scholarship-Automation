# 🎓 Scholarship Automation System
> Streamlining the scholarship process through digital automation 🚀

## 📋 Overview

The Scholarship Automation System is a web-based platform designed to simplify and digitize the traditional scholarship application process in our college. Our solution transforms the manual, time-consuming scholarship workflow into an efficient, automated system that benefits both students and administrative staff.

## Current Process

![Current Process Diagram](./assets/image.png)


## 🎯 Problem Statement

![Problem Statement Diagram](./assets/image-1.png)


## ✨ Features
### 📱 For Students
- Email-based registration with college email validation
- OTP verification system
- Document upload system
- Document verification using AI
- Appointment booking
- Application status tracking
- Progress monitoring
- Viewing Previous Applications

### 👨‍💼 For Administration
- Appointment management
- Application status updates
- Student data management
- Circular uploads

### For Faculty
- Mark unavailable dates
- Upload time table 



## 🛠 Technology Stack

### Backend
- Python 3.x
- Flask
- SQLAlchemy
- SQLite

### Frontend
- HTML5
- TailwindCSS
- JavaScript
- Font Awesome Icons

### Authentication
- Session-based authentication
- Email verification

### 🔍 OCR Capabilities
- Document text extraction using Tesseract OCR
- Support for multiple document types:
  - Aadhaar Card
  - Allotment Orders
  - Bonafide Certificates
  - Previous Memos
  - Transfer Certificates
- Advanced preprocessing for better accuracy:
  - Image enhancement
  - Rotation correction
  - Noise reduction
  - Handwritten text detection
- Smart validation system:
  - Keyword detection
  - Pattern matching
  - Document type classification
  - Error correction for common OCR mistakes
- Quality assessment:
  - Confidence scoring
  - Multiple OCR strategies
  - Best result selection

### OCR Dependencies
- Tesseract OCR Engine
- OpenCV for image processing
- PIL/Pillow for image handling
- NumPy for array operations
- python-tesseract wrapper

## Installation

1. Clone the repository
```bash
git clone <repository-url>
cd scholarship-portal
```

2. Create virtual environment
```bash
python -m venv venv
.\venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
```bash
# Create .env file
SECRET_KEY=your_secret_key
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your_email
MAIL_PASSWORD=your_app_password
```

5. Initialize database
```bash
python create_db.py
```

6. Run the application
```bash
python main.py
```


## 📊 Process Structure

```
scholarship-portal/
├── main.py                 # Application entry point
├── models.py              # Database models
├── utils.py              # Utility functions
├── create_db.py          # Database initialization
├── requirements.txt      # Project dependencies
├── static/              # Static files
│   ├── css/           # Stylesheets
│   ├── js/           # JavaScript files
│   └── uploads/      # Uploaded files
└── templates/         # HTML templates
    ├── admin/       # Admin templates
    └── student/     # Student templates
```


## 🌟 Benefits

- ⏱ Reduced processing time
- 📝 Paperless workflow
- 🔍 Enhanced transparency
- ❌ Minimized errors
- 📊 Better tracking and monitoring
- 🔐 Secure data handling





## 🙏 Acknowledgments

- Faculty members
- HOD
- Academic section staff
- Meeseva center
```

---

Built with ❤ by [Nusrahkhan](https://github.com/Nusrahkhan)