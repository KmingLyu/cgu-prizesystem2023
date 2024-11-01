from flask import Flask, request, render_template, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:your_password@your_host/your_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 定義模型
class Participants(db.Model):
    __tablename__ = 'participants'
    seqNum = db.Column(db.Integer, primary_key=True)
    departName = db.Column(db.String(50))
    name = db.Column(db.String(40))
    enter = db.Column(db.Boolean, default=False)

class Prize(db.Model):
    __tablename__ = 'prize'
    prizeId = db.Column(db.Integer, primary_key=True)
    prizeName = db.Column(db.String(50))
    quantity = db.Column(db.Integer)

class Winning(db.Model):
    __tablename__ = 'winning'
    seqNum = db.Column(db.Integer, primary_key=True)
    prizeId = db.Column(db.Integer, primary_key=True)
    # prizeSeq = db.Column(db.Integer, nullable=False)
    claimed = db.Column(db.Boolean, default=False)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == 'username' and password == 'password':
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return '使用者名稱或密碼錯誤！'
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/', methods=['GET'])
def index():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    return render_template('input_prize.html', 
                            prizes=Prize.query.all(), 
                            winnings=Winning.query.all(),
                            message=None, 
                            error=False)

@app.route('/handle_actions01', methods=['POST'])
def handle_actions01():
    # print("Action route triggered")
    action = request.form.get('action')
    selected_ids = request.form.getlist('selected')
    # print("Action:", action)
    # print("Selected IDs:", selected_ids)

    # 從表單中獲取數據
    prizeId = request.form.get('prizeId')
    # print('prizeID:', prizeId)
    # 檢查是否為空
    # 確保有獎品ID被提交
    if not prizeId:
        return render_template('input_prize.html', 
                                prizes=Prize.query.all(), 
                                winnings=Winning.query.all(),
                                message='請輸入獎品', 
                                error=True)
    # 查詢所選擇的獎品訊息
    prize = Prize.query.filter_by(prizeId=prizeId).first()

    # 根據所選的動作進行不同的處理
    if action == '選擇得獎人':
        if prize:
            # 計算獎品的剩餘數量
            total_winnings = Winning.query.filter_by(prizeId=prizeId).count()
            remaining_quantity = prize.quantity - total_winnings

            # 執行聯合查詢，顯示該獎品目前的所有中獎者
            winners = db.session.query(
                Winning.seqNum,
                Participants.name,
                Winning.claimed
            ).join(Participants, Winning.seqNum == Participants.seqNum) \
            .filter(Winning.prizeId == prizeId) \
            .all()

            return render_template('input_winner.html', 
                                    prize=prize,
                                    winners=winners,
                                    remaining=remaining_quantity,
                                    message=None, 
                                    error=False)
    elif action == '得獎名單':
    # else:
        # 執行聯合查詢，顯示該獎品目前的所有中獎者
        winnings_query = db.session.query(
            Winning.seqNum,
            Winning.claimed,
            Participants.name
        ).join(Participants, Winning.seqNum == Participants.seqNum) \
        .filter(Winning.prizeId == prizeId) \
        .all()

        # 跳轉到刪除頁面，並傳遞得獎者列表
        return render_template('delete_winner.html', prize=prize, winnings_query=winnings_query)

@app.route('/input_winner', methods=['GET', 'POST'])
def input_winner():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    prizeId = request.args.get('prizeId') if request.method == 'GET' else request.form.get('prizeId')

    if prizeId is None:
        # 獎品ID無效
        return redirect(url_for('index'))

    prize = Prize.query.filter_by(prizeId=prizeId).first()
    if not prize:
        # 無效的獎品ID
        return redirect(url_for('index'))

    # 提前計算剩餘獎品數量
    total_winnings = Winning.query.filter_by(prizeId=prizeId).count()
    remaining = prize.quantity - total_winnings

    # 執行聯合查詢，顯示該獎品目前的所有中獎者
    winners = db.session.query(
                    Winning.seqNum,
                    Participants.name,
                    Winning.claimed
                ).join(Participants, Winning.seqNum == Participants.seqNum) \
                .filter(Winning.prizeId == prizeId) \
                .all()



    if request.method == 'POST':
        seqNum = request.form.get('seqNum')

        # seq_num = int(seqNum)

        # 檢查序號是否在participants資料表中
        if not Participants.query.filter_by(seqNum=seqNum).first():
            # 序號輸入錯誤
            return render_template('input_winner.html', prize=prize, remaining=remaining, winners=winners, message='序號輸入錯誤', error=True)
        # 檢查是否還有剩餘獎品
        if remaining <= 0:
            # 獎品已經領完了
            return render_template('input_winner.html', prize=prize, remaining=remaining, winners=winners, message='獎品已經領完了 請選取其他獎品', error=True)
        # 查詢中獎者資訊
        winner = Participants.query.filter_by(seqNum=seqNum).first()
        # 檢查此人是否已領獎
        existing_winning = Winning.query.filter_by(seqNum=seqNum).first()
        if existing_winning:
            message = f'{winner.seqNum} - {winner.name} 已輸入過了'
            # 此人已輸入過了
            return render_template('input_winner.html', prize=prize, remaining=remaining, winners=winners, message=message, error=True)
        # 創建新的 Winning 實例並添加到資料庫
        winning = Winning(seqNum=seqNum, prizeId=prizeId, claimed=False)
        db.session.add(winning)
        db.session.commit()
        remaining -= 1  # 更新剩餘獎品數量

    message = f'{winner.seqNum} - {winner.name} 新增成功'
    # 執行聯合查詢，顯示該獎品目前的所有中獎者
    winners = db.session.query(
                    Winning.seqNum,
                    Participants.name,
                    Winning.claimed
                ).join(Participants, Winning.seqNum == Participants.seqNum) \
                .filter(Winning.prizeId == prizeId) \
                .all()
    # print(winners)

    # if remaining > 0:
    # 獎品還有剩餘，重新導回 input_winner.html
    return render_template('input_winner.html', prize=prize, remaining=remaining, winners=winners, message=message, error=False)

    # 從新導回首頁
    # return render_template('input_prize.html', 
    #                         prizes=Prize.query.all(), 
    #                         winnings=Winning.query.all(),
    #                         message=message, 
    #                         error=False)

@app.route('/delete_winner', methods=['GET', 'POST'])
def delete_winner():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    prizeId = request.args.get('prizeId') if request.method == 'GET' else request.form.get('prizeId')
    if request.method == 'POST':
        # 從表單中獲取動作和被選中的ID
        action = request.form.get('action')
        selected_ids = request.form.getlist('selected')

        for selected_id in selected_ids:
            seqNum = int(selected_id)
            winning_entry = Winning.query.filter_by(seqNum=seqNum).first()
            if not winning_entry:
                continue
            # if action == '刪除':
            db.session.delete(winning_entry)

        # 提交所有更改到數據庫
        db.session.commit()

        prize = Prize.query.filter_by(prizeId=prizeId).first()
        # 執行聯合查詢，顯示該獎品目前的所有中獎者
        winnings_query = db.session.query(
            Winning.seqNum,
            Winning.claimed,
            Participants.name
        ).join(Participants, Winning.seqNum == Participants.seqNum) \
        .filter(Winning.prizeId == prizeId) \
        .all()

        # 跳轉到刪除頁面，並傳遞得獎者列表
        return render_template('delete_winner.html', prize=prize, winnings_query=winnings_query)
    

@app.route('/winning_list', methods=['GET', 'POST'])
def winning_list():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    # 執行聯合查詢並按照 prizeId 排序
    # 顯示資訊包含: seqNum, name, prizeId, prizeName, claimed
    winnings_query = db.session.query(
        Winning.seqNum,
        Winning.prizeId,
        Winning.claimed,
        Participants.name,
        Prize.prizeName
    ).join(Participants, Winning.seqNum == Participants.seqNum) \
    .join(Prize, Winning.prizeId == Prize.prizeId) \
    .order_by(Winning.prizeId) \
    .all()

    return render_template('winning_list.html', winnings_query=winnings_query)

@app.route('/handle_actions', methods=['POST'])
def handle_actions():
    # print("Action route triggered")
    action = request.form.get('action')
    selected_ids = request.form.getlist('selected')
    # print("Action:", action)
    # print("Selected IDs:", selected_ids)

    for selected_id in selected_ids:
        seqNum, prizeId = map(int, selected_id.split('-'))
        winning_entry = Winning.query.filter_by(seqNum=seqNum, prizeId=prizeId).first()
        if not winning_entry:
            continue
        if action == '領獎':
            winning_entry.claimed = True
        elif action == '刪除':
            db.session.delete(winning_entry)
    db.session.commit()
    return redirect(url_for('winning_list'))

if __name__ == '__main__':
    app.run(debug=True)
