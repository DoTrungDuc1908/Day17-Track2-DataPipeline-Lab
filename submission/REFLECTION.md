# Reflection — Day 17 (≤ 200 words)

Answer briefly, in your own words. This is graded on reasoning, not length.

1. **The flywheel.** Day 13 emitted agent traces; today you turned them into an
   eval set and DPO pairs that Day 22 will train on. Which step in
   `traces → Bronze → datasets` would break most silently in production if you
   got it wrong — and how would you detect it?
   
   *Trả lời:* Bước trải phẳng đệ quy (`traces_to_bronze`) hoặc phân loại trace. Việc nhận diện sai trạng thái lỗi thành công sẽ âm thầm làm nhiễm độc các cặp DPO (tráo đổi chosen/rejected). Phát hiện bằng cách giám sát tỷ lệ ok/error và kiểm tra schema đầu ra.

2. **Decontamination.** Your run dropped 2 of 3 preference pairs because their
   prompts were in the eval set. What concretely goes wrong if you *skip* this
   step and train on those pairs? How would the lie show up in your metrics?
   
   *Trả lời:* Gây rò rỉ dữ liệu (data leakage) khi mô hình học thuộc lòng câu hỏi của bài thi. Chỉ số win rate trên tập Eval sẽ cao ảo tưởng (gần 100%), nhưng mô hình chạy thực tế sẽ không thể tổng quát hóa và cho kết quả kém.

3. **Point-in-time.** The naive join leaked a future `lifetime_spend` into the
   training row. Describe one feature in a system you know that would be
   dangerous to join without an `ASOF`/point-in-time guard.
   
   *Trả lời:* Điểm tín dụng hoặc trạng thái khóa tài khoản trong hệ thống chống gian lận. Nếu nối trạng thái hiện tại về thời điểm giao dịch trong quá khứ sẽ gây rò rỉ dữ liệu tương lai, dẫn đến lệch pha huấn luyện (offline-online skew).

4. **Graph vs vector.** From `kg_demo.py`, name one question the knowledge graph
   answers well that flat chunk retrieval (`embed.py`) would struggle with, and
   one where the graph is overkill.
   
   *Trả lời:* Câu hỏi đa bước như "widgets được vận chuyển từ đâu?" được giải quyết tốt bởi đồ thị nhờ liên kết các dữ kiện bắc cầu nằm ở các chunk tách biệt. Còn tra cứu trực tiếp như "hạn bảo hành của gadget" thì dùng vector search sẽ nhanh và tối ưu hơn.
