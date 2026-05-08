# XPerms — Plugin Quản Lý Rank & Permission cho Endstone

Plugin quản lý phân quyền (Rank/Permission) và tiền tố (Prefix/Suffix) cho người chơi trên server Minecraft Bedrock Edition (Endstone).

Lấy cảm hứng từ **LuckPerms** nhưng được thiết kế **cực kỳ đơn giản**, nhẹ nhàng và dễ đọc.

## Cấu Trúc Thư Mục

```
bedrock_server/plugins/XPerms/
├── AGENTS.md                               # Hướng dẫn cho AI
├── README.md                               # File này
├── pyproject.toml                          # File packaging
├── src/
│   └── endstone_xperms/
│       ├── __init__.py                     # Export class XPermsPlugin
│       ├── plugin.py                       # Class chính — khai báo lệnh, xử lý command
│       ├── storage.py                      # Lưu trữ dữ liệu bằng JSON
│       ├── listener.py                     # Xử lý sự kiện chat & join
│       └── config.toml                     # Config mặc định (bundled)
├── config.toml                             # Config (tự sinh khi plugin chạy lần đầu)
└── data.json                               # Dữ liệu group & user (tự sinh)
```

## Cài Đặt & Chạy

### 1. Cài đặt plugin (Editable Mode — phát triển)

```bash
cd E:\SERVER
.\.venv\Scripts\python.exe -m pip install -e .\bedrock_server\plugins\XPerms
```

### 2. Khởi động server Endstone

```bash
cd E:\SERVER\bedrock_server
endstone
```

### 3. Tải lại plugin (không cần restart server)

Trong game hoặc console, gõ: `/reload`

## Lệnh

Tất cả lệnh nằm dưới `/xperms` — cần quyền `xperms.admin` (mặc định: OP).

| Lệnh | Mô tả |
|---|---|
| `/xperms groups` | Liệt kê tất cả group |
| `/xperms group <tên> create` | Tạo group mới |
| `/xperms group <tên> delete` | Xóa group (chuyển user về default) |
| `/xperms group <tên> info` | Xem thông tin group |
| `/xperms group <tên> setprefix <prefix>` | Đặt prefix (hỗ trợ §color) |
| `/xperms group <tên> setsuffix <suffix>` | Đặt suffix |
| `/xperms group <tên> addperm <perm>` | Thêm permission |
| `/xperms group <tên> removeperm <perm>` | Xóa permission |
| `/xperms user <player> setgroup <group>` | Gán group cho player |
| `/xperms user <player> info` | Xem thông tin player |
| `/xperms reload` | Tải lại dữ liệu & config |

## Ví Dụ Sử Dụng

```
/xperms group vip create
/xperms group vip setprefix §a[VIP]
/xperms group admin create
/xperms group admin setprefix §c[Admin]
/xperms group admin addperm xperms.admin
/xperms user HuyBao setgroup admin
```

## Config

File `config.toml` (tự sinh vào `plugins/XPerms/config.toml`):

```toml
default_group = "default"
chat_format = "{prefix} {name}{suffix}§r: {message}"
```

- `default_group`: Tên group mặc định cho người chơi mới
- `chat_format`: Format tin nhắn chat với placeholder `{prefix}`, `{name}`, `{suffix}`, `{message}`
