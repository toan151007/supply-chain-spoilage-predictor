# AGENTS.md — Supply Chain Spoilage Predictor

## Project Overview

Nền tảng Quản trị Chuỗi cung ứng Chống lãng phí cho chuỗi cửa hàng bán lẻ/F&B.
Mục tiêu: Dự báo nhu cầu, tối ưu nhập hàng, giảm lãng phí thực phẩm.

## Tech Stack

- Frontend: React.js + Vite + Tailwind CSS
- Backend: Python FastAPI (hoặc Node.js/Express)
- Database: PostgreSQL
- AI/ML: Prophet, XGBoost, ARIMA (Python)
- Real-time: WebSocket
- AI Agent: Gemini API (chatbot hỏi đáp kho)

## Commands

- Cài đặt backend: `pip install -r backend/requirements.txt`
- Chạy backend: `uvicorn app.main:app --reload --port 8000`
- Cài đặt frontend: `cd frontend && npm install`
- Chạy frontend: `npm run dev` (cổng 3000)
- Chạy database: `psql -U postgres -d spoilage_predictor`
- Import SQL schema: `psql -U postgres -d spoilage_predictor -f database/01-schema/02-create-tables.sql`
- Chạy AI model: `cd ai-model && jupyter notebook`

## Project Structure

- /backend/ FastAPI server (models, routers, services)
- /frontend/ React app (components, pages, services)
- /ai-model/ Jupyter notebooks + Python models
- /database/ SQL schema, seed, queries
- /docs/ Tài liệu đồ án (báo cáo, thiết kế, timeline)
- /datasets/ Dữ liệu mẫu (raw, processed)
- /tests/ Unit tests

## Rules (BẮT BUỘC TUÂN THỦ)

- KHÔNG dùng PHP, ASP.NET, hay bất kỳ framework nào ngoài danh sách trên.
- KHÔNG sửa file cấu hình (config.py, .env) mà không hỏi trước.
- Mọi API phải có prefix `/api/v1/`.
- Mọi truy vấn database phải qua ORM, KHÔNG viết raw SQL trong routers.
- Đặt tên file Python: snake_case. Tên React component: PascalCase.
- Trước khi commit, chạy `git status` để kiểm tra.

## Known Issues & Gotchas

- Token Antigravity có giới hạn → cần commit thường xuyên.
- Khi chuyển sang Cursor/OpenCode, PHẢI yêu cầu AI đọc file AGENTS.md trước.
- WebSocket cần bật CORS cho frontend localhost:3000.

## Current Progress

- [x] Cấu trúc thư mục đã tạo trên GitHub
- [x] T1: Viết README.md chính cho dự án (hoàn thành 5/10)
- [x] T3: Viết sơ đồ kiến trúc hệ thống (hoàn thành 5/10)
- [x] T4 (phần 1): Viết xong Chương 1 (docs/02-bao-cao/chuong-1-tong-quan.md) — hoàn thành 6/10
- [ ] T4 (phần 2): Đang viết Chương 2 (docs/02-bao-cao/chuong-2-co-so-ly-thuyet.md)
- [ ] Viết SQL Schema (đang làm)
- [ ] Setup Backend FastAPI
- [ ] Setup Frontend React
- [ ] Tích hợp AI Model
