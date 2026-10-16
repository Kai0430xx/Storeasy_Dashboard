
# 背景通知部署

GitHub Pages 只發布前端。關閉網站後更新通知與圖示數字，
還必須部署 notifications Cloud Functions。
需要 Blaze 與具有部署、Secret Manager 權限的專案帳號。
Cloud Functions、Firestore、Cloud Scheduler 與 Secret Manager 依用量計費。

店長收到所屬據點候補黃點、需求到期紅點及可查看待辦紅點。
主管、管理員只收明確指派自己的主事項或子項目所屬待辦。
同帳號電腦讀取一筆，背景服務傳送剩餘絕對數量到所有啟用裝置：
4→3，讀完→0。每筆事項或候補只計一次。

## 首次部署

先完成 GitHub 更新及 Actions，再於 Google Cloud Shell 執行：

    gcloud config set project storeasy-dashboard
    gcloud services enable secretmanager.googleapis.com
    git clone https://github.com/Kai0430xx/Storeasy_Dashboard.git storeasy-push
    cd storeasy-push
    npm ci
    npm --prefix functions ci --ignore-scripts
    node functions/setup-push.mjs storeasy-dashboard https://kai0430xx.github.io/Storeasy_Dashboard/
    npx firebase login --no-localhost
    npx firebase deploy --only functions:notifications,firestore:rules --project storeasy-dashboard

資料夾已存在時進入既有儲存庫並 git pull --ff-only，不重複 clone。
setup-push.mjs 沿用既有金鑰，不要刪除或重新產生金鑰。
私鑰只存 Secret Manager，不貼入網頁或 GitHub。
functions/.secret.local 及 functions/.env.* 不可加入 Git。

第一次部署可能要求啟用相關 API 與建立 Google 服務身分。
Eventarc service agent 尚未就緒時，等建立完成再重試同一部署指令。
權限被拒請由專案管理者處理 IAM，不放寬 Firestore 規則。

## 啟用與驗證

1. iPhone 使用 iOS 16.4+ Safari → 分享 → 加入主畫面。
2. 從桌面圖示登入，點頂端鈴鐺「通知設定」。
3. 點「開啟此裝置通知」並允許系統通知；每台裝置各自啟用。
4. 手機關閉網站，由另一帳號建立符合通知範圍的提醒。
5. 同帳號電腦讀完一筆，手機應由 4→3，全部讀完清除數字。
6. 驗證未指派主管的待辦不通知主管，候補到期通知店長。
7. 登出會清除本機圖示數字與訂閱，不沿用到其他帳號。

推播不含姓名、電話、對話或備註。
背景 Web Push 需顯示系統通知，不能保證完全靜默只改數字。
數字下降採靜音通知。圖示數字依作業系統、瀏覽器與桌面支援。
網路、專注模式、省電及系統排程可能造成延遲。

後續修改 Functions 仍須重新 deploy；只更新 Pages 不會更新背景服務。
佇列即時處理，未完成工作由每分鐘排程補處理，
候補到期於台灣時間午夜重新計算。


<!-- mobile-notification-update-v1 -->
主管與管理員也接收自己負責據點的候補配對及到期提醒。電腦到「帳號與權限 → 我的負責據點」設定；手機從鈴鐺設定。電腦不顯示鈴鐺。這次背景條件修改須重新部署 functions:notifications，不需重建金鑰。
