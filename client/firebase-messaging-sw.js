
// UnoClick client/firebase-messaging-sw.js — background push + click actions
importScripts('https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js')
importScripts('https://www.gstatic.com/firebasejs/10.12.2/firebase-messaging-compat.js')

firebase.initializeApp({
  apiKey: "YOUR_FIREBASE_API_KEY",
  authDomain: "YOUR_FIREBASE_PROJECT.firebaseapp.com",
  projectId: "YOUR_FIREBASE_PROJECT",
  storageBucket: "YOUR_FIREBASE_PROJECT.appspot.com",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_APP_ID"
})
const messaging = firebase.messaging()

self.addEventListener('notificationclick', function(event) {
  const data = event.notification?.data || {}
  if (event.action === 'approve' && data.approveUrl) {
    event.waitUntil(clients.openWindow(data.approveUrl))
  }
  event.notification.close()
})
