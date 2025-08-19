
// UnoClick client/app.js — registers service worker, gets FCM token, test push
import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js'
import { getMessaging, getToken, onMessage } from 'https://www.gstatic.com/firebasejs/10.12.2/firebase-messaging.js'

const cfg = {
  apiKey: "YOUR_FIREBASE_API_KEY",
  authDomain: "YOUR_FIREBASE_PROJECT.firebaseapp.com",
  projectId: "YOUR_FIREBASE_PROJECT",
  storageBucket: "YOUR_FIREBASE_PROJECT.appspot.com",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_APP_ID",
  vapidKey: "YOUR_WEB_PUSH_PUBLIC_VAPID_KEY"
}

const app = initializeApp(cfg)
const messaging = getMessaging(app)

const status = document.getElementById('status')
const tokenEl = document.getElementById('token')
const copyBtn = document.getElementById('copy')
const testBtn = document.getElementById('test')
const serverEl = document.getElementById('server')

navigator.serviceWorker.register('/firebase-messaging-sw.js').then(async reg => {
  status.textContent = 'Service worker registered. Requesting notification permission…'
  const perm = await Notification.requestPermission()
  if (perm !== 'granted') { status.textContent = 'Notifications denied.'; return }
  try {
    const token = await getToken(messaging, { vapidKey: cfg.vapidKey, serviceWorkerRegistration: reg })
    tokenEl.value = token
    status.textContent = 'Ready. Token generated.'
    onMessage(messaging, p => alert((p.notification?.title||'Alert')+'\n'+(p.notification?.body||'')))
  } catch (e) { status.textContent = 'Token error: '+e }
})

copyBtn.onclick = () => navigator.clipboard.writeText(tokenEl.value)

testBtn.onclick = async () => {
  const token = tokenEl.value.trim(); const server = serverEl.value.trim()
  if (!token || !server) return alert('Enter Server URL and ensure token is present')
  const r = await fetch(server + '/notify/test', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({token})})
  alert('Test push: ' + (r.ok ? 'sent' : 'failed'))
}
