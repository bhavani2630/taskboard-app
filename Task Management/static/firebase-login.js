const firebaseConfig = {
  apiKey: "AIzaSyDU0O8Uevn8S8YfE2y0YaW_2exmOya48cY",
  authDomain: "taskboard-app-5d3f5.firebaseapp.com",
  projectId: "taskboard-app-5d3f5",
  storageBucket: "taskboard-app-5d3f5.appspot.com",
  messagingSenderId: "108835039137",
  appId: "1:108835039137:web:0cbeaa559443302997cde0",
  measurementId: "G-XS7NL9DS1R"
};

firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();

function signIn() {
    const provider = new firebase.auth.GoogleAuthProvider();
    auth.signInWithPopup(provider).then(result => {
        return result.user.getIdToken();
    }).then(token => {
        Cookies.set("token", token);
        window.location.href = "/main";
    }).catch(console.error);
}
