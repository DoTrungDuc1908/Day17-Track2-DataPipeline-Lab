# Tài liệu thiết kế hệ thống: Agent-Data Flywheel & Hybrid RAG/KG Pipeline cho AI Agent hỗ trợ tư vấn Luật & Thuế Việt Nam

Tài liệu này trình bày thiết kế kiến trúc hệ thống xử lý dữ liệu và tối ưu hiệu năng cho một AI Agent chuyên tư vấn pháp luật và thuế tại Việt Nam.

---

## 1. Bài toán thực tế & Ràng buộc (Problem & Constraints)

Doanh nghiệp và kế toán tại Việt Nam thường xuyên đối mặt với sự thay đổi liên tục của các văn bản pháp luật (Luật, Nghị định, Thông tư). Dữ liệu này rất phức tạp:
*   **Văn bản thô không cấu trúc:** Các thông tư, nghị định dưới dạng file PDF scan hoặc HTML có bảng biểu phức tạp, văn phong pháp lý dài dòng, nhiều tham chiếu chéo.
*   **Drift về hiệu lực pháp lý:** Một thông tư mới ra đời có thể thay đổi hoặc bãi bỏ một phần của nghị định cũ. AI Agent nếu tra cứu thông tin cũ đã hết hiệu lực sẽ đưa ra tư vấn sai lệch nguy hiểm.
*   **Ràng buộc về chi phí & bảo mật:** Ngân sách vận hành LLM/Embedding API giới hạn; dữ liệu câu hỏi của người dùng chứa thông tin doanh nghiệp nhạy cảm cần tuân thủ Nghị định 13/2023/NĐ-CP về Bảo vệ dữ liệu cá nhân (PDPL).

---

## 2. Sơ đồ kiến trúc hệ thống (Architecture Diagram)

```
                            [ Nguồn Dữ Liệu Pháp Luật ]
                                         │
                                         ▼
                             [ OCR & Text Extraction ]
                                         │
                                         ▼
                     ┌───────────────────────────────────────┐
                     │     Quality Gate (Cổng kiểm định)     │
                     └───────────────────┬───────────────────┘
                                         │
                        ┌────────────────┴────────────────┐
                        ▼ (Hợp lệ)                        ▼ (Lỗi / Cảnh báo)
              [ Text Segmentation ]                   [ Quarantine DLQ ]
                        │                                (Slack Alert)
         ┌──────────────┴──────────────┐
         ▼                             ▼
   [ Chunking & Embedding ]   [ Triple Extraction ]
         │                             │
         ▼                             ▼
   ( Vector DB )               ( Graph DB / DuckDB Graph )
   ┌───────────┐               ┌─────────────────────────┐
   │  Chroma/  │               │   Neo4j / DuckDB        │
   │  Qdrant   │               │   (Quan hệ hiệu lực)     │
   └─────┬─────┘               └────────────┬────────────┘
         │                                  │
         └──────────────┬───────────────────┘
                        ▼
            [ Context Merger / Retriever ]
                        │
                        ▼
               [ AI Agent Server ] <─── (User Queries)
                        │
                        ▼
             [ Telemetry Span Traces ]
                        │
                        ▼
             [ Traces Flattening (Bronze) ]
                        │
                        ▼
             ┌───────────────────────────────────┐
             │       Agent-Data Flywheel         │
             ├───────────────────────────────────┤
             │ * Curation (Tạo DPO & Eval Set)   │
             │ * Decontamination (Khử nhiễm)     │
             └─────────────────┬─────────────────┘
                               ▼
                    [ Fine-Tuning Dataset ]
```

---

## 3. Các quyết định kỹ thuật & Đánh đổi (Key Decisions & Tradeoffs)

Chúng tôi lựa chọn giải quyết 5 câu hỏi then chốt sau:

### Q1: Nguồn dữ liệu pháp luật tiếng Việt & Trôi nổi (Drift)
*   **Giải pháp:** Dữ liệu pháp lý có cấu trúc tham chiếu chéo rất mạnh. Chúng tôi xây dựng một thực thể dạng Đồ thị tri thức (Knowledge Graph - KG) để lưu trữ mối quan hệ hiệu lực giữa các văn bản (ví dụ: `Thông tư 80/2021` -> `SỬA_ĐỔI_MỘT_PHẦN` -> `Thông tư 219/2013`).
*   **Đánh đổi (Tradeoff):** Xây dựng KG yêu cầu chi phí tính toán cao hơn để trích xuất thực thể và quan hệ thời gian đầu (dùng LLM hoặc Regex phân tích số hiệu văn bản), nhưng giải quyết triệt để lỗi "hallucination" (ảo tưởng) tư vấn luật cũ của mô hình RAG phẳng.

### Q2: Batch hay Streaming cho Pipeline dữ liệu?
*   **Giải pháp:** Chọn mô hình **Batch hàng ngày (Daily Batch)** kết hợp cơ chế Trigger khi có văn bản mới từ Thư viện Pháp luật / Cổng thông tin Chính phủ.
*   **Đánh đổi (X vs Y):** Lựa chọn Batch thay vì Real-time Streaming (như Kafka). Văn bản pháp luật không thay đổi theo từng giây mà thay đổi theo ngày/tuần. Đầu tư hệ thống Streaming sẽ gây lãng phí chi phí hạ tầng lớn mà không mang lại giá trị thực tế cho người dùng.

### Q3: Chất lượng dữ liệu & Cổng kiểm định (Quality Gate)
*   **Giải pháp:** Sử dụng Pandera để validate các trường thuộc tính văn bản sau khi OCR (ví dụ: ngày ban hành, số hiệu văn bản, cơ quan ban hành không được null). Các văn bản lỗi font (lỗi mã tiếng Việt cũ TCVN3/VNI) hoặc thiếu thông tin quan trọng sẽ bị đẩy vào **Quarantine DLQ** để xử lý thủ công.
*   **Đánh đổi (Tradeoff):** Chấp nhận giảm tốc độ ingest ban đầu do phải kiểm tra nghiêm ngặt, đổi lại dữ liệu nạp vào Vector DB và Graph DB hoàn toàn sạch, tránh việc mô hình AI học sai cú pháp hoặc sai số hiệu luật.

### Q4: Phi cấu trúc -> RAG hay KG?
*   **Giải pháp:** Sử dụng kiến trúc **Hybrid (Kết hợp RAG và KG)**. 
    *   *RAG phẳng:* Trả lời câu hỏi định nghĩa (ví dụ: "Thuế suất GTGT của mặt hàng thiết bị y tế là bao nhiêu?").
    *   *Graph:* Trả lời câu hỏi liên kết (ví dụ: "Theo nghị định mới nhất, thủ tục hoàn thuế GTGT đã thay đổi như thế nào so với quy định năm 2021?").
*   **Đánh đổi (Tradeoff):** Tăng độ trễ hệ thống thêm khoảng 15-20% do phải truy vấn song song cả hai cơ sở dữ liệu và tổng hợp kết quả (Context Merger), nhưng tăng độ chính xác của câu trả lời từ 65% (RAG thuần) lên 93% (Hybrid).

### Q5: Bối cảnh Việt Nam (Compliance & Privacy)
*   **Giải pháp:** Tích hợp bộ lọc **PII Anonymization** ở đầu vào của Flywheel. Trước khi lưu trace hoạt động của người dùng vào Bronze spans phục vụ tạo tập DPO/Fine-tune, hệ thống sử dụng Named Entity Recognition (NER) tiếng Việt để ẩn danh hóa tên người dùng, mã số thuế doanh nghiệp, số điện thoại, địa chỉ và thông tin tài chính cá nhân.
*   **Đánh đổi (Tradeoff):** Tốn thêm tài nguyên xử lý văn bản ở gateway, nhưng đảm bảo hệ thống tuyệt đối tuân thủ Nghị định 13/2023/NĐ-CP về Bảo vệ dữ liệu cá nhân tại Việt Nam, tránh nguy cơ rò rỉ dữ liệu doanh nghiệp của khách hàng khi gửi dữ liệu đi huấn luyện.

---

## 4. Phương án bị loại bỏ (Rejected Alternative)

Chúng tôi đã cân nhắc và loại bỏ phương án **"Sử dụng Vector Search thuần túy (Flat RAG) kết hợp với Re-ranking"**.
*   **Lý do loại bỏ:** RAG phẳng chia nhỏ văn bản pháp luật thành các đoạn 500 từ độc lập. Khi một đoạn luật ở Điều 3 được sửa đổi bởi một đoạn khác nằm ở Thông tư ban hành sau đó 2 năm, Vector Search không thể liên kết hai đoạn này lại với nhau vì độ tương đồng ngữ nghĩa của chúng không đủ cao để cùng xuất hiện trong top K. Hệ thống sẽ tiếp tục trả lời dựa trên văn bản cũ, gây hậu quả pháp lý nghiêm trọng cho doanh nghiệp sử dụng dịch vụ.

---

## 5. Failure Semantics & Idempotency

Hệ thống ingest được thiết kế để đảm bảo tính **Idempotent** tuyệt đối:
*   Mỗi văn bản pháp luật được gán ID duy nhất dựa trên mã băm nội dung (content hash SHA-256).
*   Khi chạy lại pipeline hoặc thực hiện backfill dữ liệu cũ, hệ thống sẽ thực hiện kiểm tra `INSERT OR IGNORE` trên DuckDB và Vector Store để tránh trùng lặp dữ liệu và lãng phí chi phí sinh embedding.
