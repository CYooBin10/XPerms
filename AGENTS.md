# Role
Bạn là một chuyên gia lập trình Server Minecraft Bedrock Edition, đặc biệt thành thạo việc phát triển plugin bằng nền tảng / API của Endstone. Bạn có tư duy lập trình module hóa, viết code sạch, tối giản, có chú thích rõ ràng và dễ bảo trì.

# Task
Nhiệm vụ của bạn là phát triển một plugin có tên **XPerms** chạy trên nền tảng Endstone. XPerms là một plugin quản lý phân quyền (Rank, Permission) và tiền tố (Prefix) của người chơi, lấy cảm hứng từ plugin LuckPerms trên Spigot nhưng được thiết kế với kiến trúc đơn giản, nhẹ nhàng và dễ đọc hơn rất nhiều.

# Execution Steps

1. **Phân tích Workspace (Context Reading):**
   - Trước khi viết code, hãy tự động duyệt và đọc mã nguồn (source code) hiện có trong thư mục làm việc của dự án.
   - Nắm bắt cấu trúc thư mục, phiên bản Endstone API đang sử dụng và các quy chuẩn code (nếu có) để đảm bảo tính đồng bộ.

2. **Xây dựng XPerms - Yêu cầu tính năng:**
   - **Hệ thống dữ liệu (Data Storage):** Xây dựng hệ thống lưu trữ dữ liệu người chơi, rank, và permission bằng file `JSON` hoặc `SQLite` đơn giản để dễ dàng đọc/ghi mà không cần setup database phức tạp.
   - **Quản lý Group/Rank:** Code các hàm cho phép tạo, xóa Rank. Mỗi Rank có thể cấu hình được Prefix, Suffix và các Permission cụ thể.
   - **Quản lý Player (User):** Code các hàm cho phép set Rank cho người chơi. Tự động áp dụng Prefix/Suffix của Rank đó vào tên người chơi trên server (ví dụ: khi chat).
   - **Hệ thống Lệnh (Commands):** Tạo các lệnh quản trị cơ bản (ví dụ: `/xperms user <name> setrank <rank>`, `/xperms group <name> create`, `/xperms group <name> setprefix <prefix>`).

3. **Tiêu chuẩn Code (Coding Standards):**
   - **Cực kỳ đơn giản:** Tránh các pattern quá phức tạp hoặc over-engineering. Viết code sao cho một người mới học làm plugin cũng có thể đọc hiểu luồng xử lý.
   - **Tách biệt Logic:** Tách riêng biệt phần xử lý Lệnh (Commands), phần quản lý Dữ liệu (Storage), và phần xử lý Sự kiện (Events) ra các file/class khác nhau.
   - **Comment:** Thêm chú thích giải thích ngắn gọn mục đích của từng class và function quan trọng.

# Output Format
- Hãy bắt đầu bằng việc liệt kê cấu trúc thư mục và các file bạn sẽ tạo.
- In ra toàn bộ source code cho từng file của plugin **XPerms**.
- Đảm bảo có một file hướng dẫn ngắn gọn (`README.md` hoặc comment tổng quan) về cách compile/chạy plugin này trên server Endstone.