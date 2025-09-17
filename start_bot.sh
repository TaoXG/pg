#echo "git pull"
#git pull origin main --rebase

PID=$(ps aux | grep chat_bot.py | grep -v grep | awk '{print $2}')
echo "kill $PID"
kill $PID
mkdir -p logs
LOG=logs/bot-$(date "+%Y%m%d%H%M").log
nohup python chat_bot.py > "$LOG" 2>&1 &
echo "bot started"
echo "Log file: $LOG"
tail -f "$LOG"
