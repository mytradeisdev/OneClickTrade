
// UnoClick client/firebase-messaging-sw.js — background push + click actions
importScripts('https://www.gstatic.com/firebasejs/10.12.2/firebase-app-compat.js')
importScripts('https://www.gstatic.com/firebasejs/10.12.2/firebase-messaging-compat.js')

firebase.initializeApp({
  apiKey: "AIzaSyDmtszoCu_PIyRZaJ2j-WvTEIC0hrp8FiY",
  authDomain: "unocliq-8ea2a.firebaseapp.com",
  projectId: "unocliq-8ea2a",
  storageBucket: "unocliq-8ea2a.firebasestorage.app",
  messagingSenderId: "824177176028",
  appId: "1:824177176028:web:ff96def4dbf0dc56e33319"
})
const messaging = firebase.messaging()

self.addEventListener('notificationclick', function(event) {
  const data = event.notification?.data || {}
  if (event.action === 'approve' && data.approveUrl) {
    event.waitUntil(clients.openWindow(data.approveUrl))
  }
  event.notification.close()
})
