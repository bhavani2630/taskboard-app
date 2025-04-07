// Import Firebase SDK
import { initializeApp } from "https://www.gstatic.com/firebasejs/11.3.1/firebase-app.js";
import { getAuth, signInWithEmailAndPassword, createUserWithEmailAndPassword, signOut } from "https://www.gstatic.com/firebasejs/11.3.1/firebase-auth.js";
import { getAnalytics } from "https://www.gstatic.com/firebasejs/11.3.1/firebase-analytics.js";

// Firebase Configuration (UPDATED)
const firebaseConfig = {
  apiKey: "AIzaSyDU0O8Uevn8S8YfE2y0YaW_2exmOya48cY",
  authDomain: "taskboard-app-5d3f5.firebaseapp.com",
  projectId: "taskboard-app-5d3f5",
  storageBucket: "taskboard-app-5d3f5.firebasestorage.app",
  messagingSenderId: "108835039137",
  appId: "1:108835039137:web:0cbeaa559443302997cde0",
  measurementId: "G-XS7NL9DS1R"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
const auth = getAuth(app);

// Firestore API Base URL (UPDATED)
const PROJECT_ID = "taskboard-app-5d3f5";
const API_KEY = "AIzaSyDU0O8Uevn8S8YfE2y0YaW_2exmOya48cY";
const FIRESTORE_URL = `https://firestore.googleapis.com/v1/projects/${PROJECT_ID}/databases/(default)/documents/users?key=${API_KEY}`;

window.addEventListener("load", function () {
    updateUI(document.cookie);

    // 🔹 SIGN UP FUNCTION
    const signUpButton = document.getElementById("sign-up");
    if (signUpButton) {
        signUpButton.addEventListener('click', function (event) {
            event.preventDefault();

            const email = document.getElementById("email").value;
            const password = document.getElementById("password").value;

            createUserWithEmailAndPassword(auth, email, password)
                .then((userCredential) => {
                    const user = userCredential.user;
                    const userId = user.uid;

                    // Store User in Firestore
                    saveUserToFirestore(userId, email);

                    // Save Token in Cookie
                    user.getIdToken().then((token) => {
                        document.cookie = "token=" + token + ";path=/;SameSite=Strict";
                        window.location = "/";
                    });
                })
                .catch((error) => {
                    console.error("Signup error: " + error.code + " " + error.message);
                    alert("Registration failed: " + error.message);
                });
        });
    }

    // 🔹 LOGIN FUNCTION
    const loginButton = document.getElementById("login");
    if (loginButton) {
        loginButton.addEventListener('click', function () {
            const email = document.getElementById("email").value;
            const password = document.getElementById("password").value;

            signInWithEmailAndPassword(auth, email, password)
                .then((userCredential) => {
                    const user = userCredential.user;
                    fetchUserFromFirestore(user.uid);
                    user.getIdToken().then((token) => {
                        document.cookie = "token=" + token + ";path=/;SameSite=Strict";
                        window.location = "/";
                    });
                })
                .catch((error) => {
                    console.error("Login error: " + error.code + " " + error.message);
                    alert("Login failed: " + error.message);
                });
        });
    }

    // 🔹 LOGOUT FUNCTION
    const signOutButton = document.getElementById("sign-out");
    if (signOutButton) {
        signOutButton.addEventListener('click', function () {
            signOut(auth)
                .then(() => {
                    document.cookie = "token=;path=/;SameSite=Strict";
                    window.location = "/";
                })
                .catch((error) => {
                    console.error("Sign-out error: " + error.message);
                    alert("Sign-out failed: " + error.message);
                });
        });
    }
});

// 🔹 SAVE USER TO FIRESTORE FUNCTION
function saveUserToFirestore(userId, email) {
    const userData = {
        fields: {
            userId: { stringValue: userId },
            email: { stringValue: email },
            createdAt: { timestampValue: new Date().toISOString() }
        }
    };

    fetch(FIRESTORE_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(userData)
    })
        .then(response => {
            if (!response.ok) throw new Error("Firestore save failed: " + response.statusText);
            return response.json();
        })
        .then(data => console.log("User saved to Firestore:", data))
        .catch(error => console.error("Error saving user:", error));
}

// 🔹 FETCH USER FROM FIRESTORE FUNCTION
function fetchUserFromFirestore(userId) {
    const url = `https://firestore.googleapis.com/v1/projects/${PROJECT_ID}/databases/(default)/documents/users/${userId}?key=${API_KEY}`;

    fetch(url)
        .then(response => response.json())
        .then(data => console.log("User fetched from Firestore:", data))
        .catch(error => console.error("Error fetching user:", error));
}

// 🔹 UPDATE UI FUNCTION
function updateUI(cookie) {
    const token = parseCookieToken(cookie);

    if (token.length > 0) {
        document.getElementById("login-box").hidden = true;
        document.getElementById("sign-out").hidden = false;
    } else {
        document.getElementById("login-box").hidden = false;
        document.getElementById("sign-out").hidden = true;
    }
}

// 🔹 PARSE COOKIE FUNCTION
function parseCookieToken(cookie) {
    const strings = cookie.split(';');
    for (let i = 0; i < strings.length; i++) {
        const temp = strings[i].trim().split('=');
        if (temp[0] === "token") return temp[1];
    }
    return "";
}
