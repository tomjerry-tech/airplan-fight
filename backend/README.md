# Backend Database

第一版后端使用 MySQL 保存长期数据：

- 玩家昵称和登录 token
- 排行榜分数
- 房间历史记录

实时房间状态不写入 MySQL，运行时保存在服务端内存中。

## 初始化

安装依赖：

```bash
pip install -r backend/requirements.txt
```

配置连接信息：

```bash
set AIRPLANE_DB_HOST=127.0.0.1
set AIRPLANE_DB_PORT=3306
set AIRPLANE_DB_USER=root
set AIRPLANE_DB_PASSWORD=your_password
set AIRPLANE_DB_NAME=airplane_game
```

初始化数据库和表：

```bash
python backend/db.py
```

启动后端：

```bash
python backend/app.py
```

运行登录接口测试：

```bash
cd backend
python -m unittest test_login.py
```

客户端联机 smoke demo：

```bash
python code/online_client_demo.py --name playerA --create
python code/online_client_demo.py --name playerB --room 123456
```

Pygame 联机可视化 demo：

```bash
python code/online_game.py
python code/online_game.py --name playerA --create
python code/online_game.py --name playerB --room 123456
```

`online_game.py` 会优先加载现有图片素材，失败时自动回退到简单图形渲染。
不带参数启动时会进入基础大厅 UI，可输入昵称、创建房间或加入房间。

一键启动开发环境：

```bash
python start_dev.py
```

Windows 也可以双击项目根目录下的：

```text
启动联机游戏.bat
```

脚本会启动后端，自动创建一个测试房间，并打开两个已自动入房的客户端窗口。MySQL 服务需要提前启动。

当前已实现接口：

```text
GET  /api/health
POST /api/login
GET  /api/rankings
GET  /api/rooms
POST /api/rooms
POST /api/rooms/<room_id>/join
POST /api/rooms/<room_id>/ready
POST /api/rooms/<room_id>/leave
```

当前不提供客户端直接提交分数的 HTTP 接口。游戏结束后由服务端内部逻辑调用 `rankings.record_score()` 写入分数。

当前已实现 Socket.IO 事件：

```text
client -> server:
join_room
player_ready
leave_room
input

server -> client:
room_update
game_start
game_state
error
```

当前 `game_state` 已实现基础同步：玩家位置、子弹、敌机、分数、道具、Boss 字段。子弹命中敌机、敌机扣血、击毁加分、双人敌机加密、基础宝石掉落、宝石拾取加分、heal/shield/upgrade 功能道具基础效果、Boss 基础生成和受击击败、Boss 基础弹幕、游戏结束结算写库已实现。Boss 阶段技能仍待扩展。
