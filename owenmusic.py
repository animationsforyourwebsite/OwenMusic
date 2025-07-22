import sys, os, json, uuid
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import Qt
import pygame
import speech_recognition as sr
from pydub import AudioSegment

pygame.mixer.init()

USERS_FILE = "users.json"
LYRICS_FOLDER = "lyrics"
SONGS_FOLDER = "songs"

os.makedirs(LYRICS_FOLDER, exist_ok=True)
os.makedirs(SONGS_FOLDER, exist_ok=True)

if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w") as f:
        json.dump({}, f)

def generate_lyrics(file_path):
    recognizer = sr.Recognizer()
    audio = AudioSegment.from_file(file_path).set_channels(1).set_frame_rate(16000)
    temp_wav = "temp.wav"
    audio.export(temp_wav, format="wav")
    with sr.AudioFile(temp_wav) as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data)
        except:
            text = "(Could not generate lyrics)"
    os.remove(temp_wav)
    return text

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OwenMusic Login")
        self.setGeometry(500, 200, 400, 250)
        self.setStyleSheet("background-color: #e6ffe6; color: #003300;")
        layout = QVBoxLayout()

        self.setWindowIcon(QIcon("owenmusic.ico"))

        self.title = QLabel("🎵 OwenMusic Login")
        self.title.setFont(QFont("Arial", 16))
        self.title.setAlignment(Qt.AlignCenter)

        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        self.password = QLineEdit()
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.Password)

        self.role = QComboBox()
        self.role.addItems(["User", "Artist"])

        self.login_btn = QPushButton("Log In / Sign Up")
        self.login_btn.clicked.connect(self.login)

        layout.addWidget(self.title)
        layout.addWidget(self.username)
        layout.addWidget(self.password)
        layout.addWidget(self.role)
        layout.addWidget(self.login_btn)
        self.setLayout(layout)

    def login(self):
        name = self.username.text().strip()
        pw = self.password.text().strip()
        role = self.role.currentText().lower()
        if not name or not pw:
            return
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
        if name in users:
            if users[name]["password"] != pw:
                QMessageBox.warning(self, "Error", "Incorrect password.")
                return
        else:
            users[name] = {
                "password": pw,
                "role": role,
                "songs": [],
                "playlists": {},
                "songcredits": {},
                "albums": {},
                "eps": {},
            }
            with open(USERS_FILE, "w") as f:
                json.dump(users, f, indent=2)
        self.main = OwenMusic(name, role)
        self.main.show()
        self.close()

class OwenMusic(QWidget):
    def __init__(self, username, role):
        super().__init__()
        self.setWindowTitle(f"OwenMusic - {username} ({role})")
        self.setStyleSheet("background-color: #eaffea; color: #003300; font-family: Arial;")
        self.setWindowIcon(QIcon("owenmusic.ico"))
        self.setGeometry(200, 100, 1100, 700)
        self.setMinimumSize(900, 600)
        self.username, self.role = username, role
        self.songs = []
        self.current_song = None

        self.playlists = {}
        self.songcredits = {}
        self.albums = {}
        self.eps = {}

        self.load_user_data()

        self.init_ui()
        self.load_user_songs()

    def load_user_data(self):
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
        user_data = users.get(self.username, {})
        self.playlists = user_data.get("playlists", {})
        self.songcredits = user_data.get("songcredits", {})
        self.albums = user_data.get("albums", {})
        self.eps = user_data.get("eps", {})

    def save_user_data(self):
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
        if self.username not in users:
            users[self.username] = {}
        users[self.username]["playlists"] = self.playlists
        users[self.username]["songcredits"] = self.songcredits
        users[self.username]["albums"] = self.albums
        users[self.username]["eps"] = self.eps
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=2)

    def init_ui(self):
        main = QVBoxLayout()
        top = QHBoxLayout()
        controls = QHBoxLayout()
        middle = QHBoxLayout()

        # Upload/Publish button for artists
        self.upload_btn = QPushButton("📤 Publish")
        self.upload_btn.clicked.connect(self.upload_song)
        self.upload_btn.setVisible(self.role == "artist")
        controls.addWidget(self.upload_btn)

        # Artist album/EP buttons
        if self.role == "artist":
            self.create_album_btn = QPushButton("➕ Create Album")
            self.create_album_btn.clicked.connect(self.create_album)
            controls.addWidget(self.create_album_btn)

            self.create_ep_btn = QPushButton("➕ Create EP")
            self.create_ep_btn.clicked.connect(self.create_ep)
            controls.addWidget(self.create_ep_btn)

            self.assign_album_btn = QPushButton("🎵 Assign Song to Album")
            self.assign_album_btn.clicked.connect(self.assign_song_album)
            controls.addWidget(self.assign_album_btn)

            self.assign_ep_btn = QPushButton("🎵 Assign Song to EP")
            self.assign_ep_btn.clicked.connect(self.assign_song_ep)
            controls.addWidget(self.assign_ep_btn)

        # Always present buttons
        self.play_btn = QPushButton("▶️ Play")
        self.play_btn.clicked.connect(self.play_song)
        controls.addWidget(self.play_btn)

        self.fullscreen_btn = QPushButton("🖥️ Fullscreen")
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        controls.addWidget(self.fullscreen_btn)

        self.logout_btn = QPushButton("🔓 Logout")
        self.logout_btn.clicked.connect(self.logout)
        controls.addWidget(self.logout_btn)

        # User playlist and search buttons
        if self.role == "user":
            self.search_btn = QPushButton("🔍 Search Songs")
            self.search_btn.clicked.connect(self.search_songs)
            controls.addWidget(self.search_btn)

            self.create_playlist_btn = QPushButton("➕ Create Playlist")
            self.create_playlist_btn.clicked.connect(self.create_playlist)
            controls.addWidget(self.create_playlist_btn)

            self.add_to_playlist_btn = QPushButton("➕ Add to Playlist")
            self.add_to_playlist_btn.clicked.connect(self.add_to_playlist)
            controls.addWidget(self.add_to_playlist_btn)

            self.clear_playlist_btn = QPushButton("❌ Exit Playlist")
            self.clear_playlist_btn.clicked.connect(self.clear_playlist_filter)
            self.clear_playlist_btn.setStyleSheet("background-color: #ffcccc; padding: 6px; border-radius: 10px;")
            controls.addWidget(self.clear_playlist_btn)

        for i in range(controls.count()):
            w = controls.itemAt(i).widget()
            if isinstance(w, QPushButton):
                w.setStyleSheet("background-color: #ccffcc; padding: 6px; border-radius: 10px;")

        top.addWidget(QLabel(f"Welcome, {self.username} ({self.role})"))
        top.addStretch()

        # Left side: song list
        self.song_list = QListWidget()
        self.song_list.itemClicked.connect(self.load_song_details)

        # Middle: lyrics box
        self.lyrics_box = QTextEdit()
        self.lyrics_box.setReadOnly(self.role != "artist")

        # Right side: playlists (users only)
        if self.role == "user":
            playlist_section = QVBoxLayout()
            playlist_label = QLabel("🎵 Playlists")
            playlist_label.setFont(QFont("Arial", 12, QFont.Bold))
            self.playlist_list = QListWidget()
            self.playlist_list.itemClicked.connect(self.load_playlist_songs)
            playlist_section.addWidget(playlist_label)
            playlist_section.addWidget(self.playlist_list)
            self.update_playlist_list()

            middle.addLayout(playlist_section, 1)

        # Song details (credits, artist, album, ep)
        details_section = QVBoxLayout()
        details_label = QLabel("🎼 Song Details")
        details_label.setFont(QFont("Arial", 12, QFont.Bold))
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        details_section.addWidget(details_label)
        details_section.addWidget(self.details_text)

        # Layout: song list | lyrics | (playlists) | details
        middle.addWidget(self.song_list, 2)
        middle.addWidget(self.lyrics_box, 3)
        if self.role == "user":
            middle.addStretch()
        middle.addLayout(details_section, 2)

        main.addLayout(top)
        main.addLayout(controls)
        main.addLayout(middle)

        self.setLayout(main)

    def update_playlist_list(self):
        if self.role != "user":
            return
        self.playlist_list.clear()
        for pl_name in self.playlists.keys():
            self.playlist_list.addItem(pl_name)

    def load_playlist_songs(self, item):
        playlist_name = item.text()
        if playlist_name not in self.playlists:
            return
        song_ids = self.playlists[playlist_name]
        self.song_list.clear()
        for s in self.songs:
            if s["id"] in song_ids:
                self.song_list.addItem(s["title"])

    def clear_playlist_filter(self):
        self.load_user_songs()
        if self.role == "user":
            self.playlist_list.clearSelection()

    def load_song_details(self, item):
        title = item.text()
        song = next((s for s in self.songs if s["title"] == title), None)
        if not song:
            return
        self.current_song = song

        # Load lyrics
        try:
            with open(os.path.join(LYRICS_FOLDER, f"{song['id']}.txt"), "r") as f:
                self.lyrics_box.setPlainText(f.read())
        except:
            self.lyrics_box.setPlainText("(Lyrics not found)")

        # Load song details
        song_id = song["id"]
        credit_info = self.songcredits.get(song_id, {})
        artist_name = credit_info.get("artist", "(No artist)")
        credits = credit_info.get("credits", "No credits available.")

        album = "(No album)"
        ep = "(No EP)"
        for alb_name, song_ids in self.albums.items():
            if song_id in song_ids:
                album = alb_name
                break
        for ep_name, song_ids in self.eps.items():
            if song_id in song_ids:
                ep = ep_name
                break

        details = f"Title: {song['title']}\nArtist: {artist_name}\nCredits: {credits}\nAlbum: {album}\nEP: {ep}"
        self.details_text.setPlainText(details)

    def toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def logout(self):
        self.close()
        self.login = LoginWindow()
        self.login.show()

    def load_user_songs(self):
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
        self.songs = users[self.username]["songs"]
        self.song_list.clear()
        for s in self.songs:
            self.song_list.addItem(s["title"])

    def upload_song(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select a song", "", "Audio Files (*.mp3 *.wav)")
        if not path:
            return
        title, ok = QInputDialog.getText(self, "Song Title", "Enter song title:")
        if not ok or not title.strip():
            return
        artist_name, ok2 = QInputDialog.getText(self, "Artist Name", "Enter artist name:")
        if not ok2 or not artist_name.strip():
            artist_name = self.username

        lyrics = generate_lyrics(path)
        song_id = str(uuid.uuid4())[:8]
        ext = os.path.splitext(path)[1]
        new_name = os.path.join(SONGS_FOLDER, f"{song_id}{ext}")
        with open(new_name, "wb") as f:
            f.write(open(path, "rb").read())
        with open(os.path.join(LYRICS_FOLDER, f"{song_id}.txt"), "w") as f:
            f.write(lyrics)
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
        users[self.username]["songs"].append({"title": title, "file": new_name, "id": song_id})
        users[self.username].setdefault("songcredits", {})[song_id] = {"artist": artist_name, "credits": "No credits yet."}
        with open(USERS_FILE, "w") as f:
            json.dump(users, f, indent=2)
        self.load_user_songs()
        self.load_user_data()
        self.update_playlist_list()

    def play_song(self):
        if not self.current_song:
            return
        pygame.mixer.music.load(self.current_song["file"])
        pygame.mixer.music.play()

    def closeEvent(self, event):
        if self.role == "artist" and self.current_song:
            updated = self.lyrics_box.toPlainText()
            with open(os.path.join(LYRICS_FOLDER, f"{self.current_song['id']}.txt"), "w") as f:
                f.write(updated)
        self.save_user_data()
        event.accept()

    def search_songs(self):
        text, ok = QInputDialog.getText(self, "Search Songs", "Enter song title keyword:")
        if ok and text.strip():
            keyword = text.strip().lower()
            self.song_list.clear()
            filtered = [s for s in self.songs if keyword in s["title"].lower()]
            for s in filtered:
                self.song_list.addItem(s["title"])
        else:
            self.load_user_songs()

    def create_playlist(self):
        name, ok = QInputDialog.getText(self, "Create Playlist", "Enter new playlist name:")
        if ok and name.strip():
            name = name.strip()
            if name in self.playlists:
                QMessageBox.warning(self, "Error", "Playlist already exists.")
                return
            self.playlists[name] = []
            self.save_user_data()
            self.update_playlist_list()
            QMessageBox.information(self, "Success", f"Playlist '{name}' created.")

    def add_to_playlist(self):
        if not self.current_song:
            QMessageBox.warning(self, "Error", "No song selected.")
            return
        if not self.playlists:
            QMessageBox.warning(self, "Error", "No playlists available. Create one first.")
            return
        playlist_name, ok = QInputDialog.getItem(self, "Add to Playlist", "Choose playlist:", list(self.playlists.keys()), 0, False)
        if ok:
            song_id = self.current_song["id"]
            if song_id in self.playlists[playlist_name]:
                QMessageBox.information(self, "Info", "Song already in playlist.")
                return
            self.playlists[playlist_name].append(song_id)
            self.save_user_data()
            QMessageBox.information(self, "Success", f"Added '{self.current_song['title']}' to '{playlist_name}'.")

    def create_album(self):
        name, ok = QInputDialog.getText(self, "Create Album", "Enter new album name:")
        if ok and name.strip():
            name = name.strip()
            if name in self.albums:
                QMessageBox.warning(self, "Error", "Album already exists.")
                return
            self.albums[name] = []
            self.save_user_data()
            QMessageBox.information(self, "Success", f"Album '{name}' created.")

    def create_ep(self):
        name, ok = QInputDialog.getText(self, "Create EP", "Enter new EP name:")
        if ok and name.strip():
            name = name.strip()
            if name in self.eps:
                QMessageBox.warning(self, "Error", "EP already exists.")
                return
            self.eps[name] = []
            self.save_user_data()
            QMessageBox.information(self, "Success", f"EP '{name}' created.")

    def assign_song_album(self):
        if not self.current_song:
            QMessageBox.warning(self, "Error", "No song selected.")
            return
        if not self.albums:
            QMessageBox.warning(self, "Error", "No albums exist. Create one first.")
            return
        album_name, ok = QInputDialog.getItem(self, "Assign to Album", "Choose album:", list(self.albums.keys()), 0, False)
        if ok:
            song_id = self.current_song["id"]
            for alb in self.albums:
                if song_id in self.albums[alb]:
                    self.albums[alb].remove(song_id)
            self.albums[album_name].append(song_id)
            self.save_user_data()
            QMessageBox.information(self, "Success", f"Assigned '{self.current_song['title']}' to album '{album_name}'.")
            self.load_song_details(QListWidgetItem(self.current_song["title"]))

    def assign_song_ep(self):
        if not self.current_song:
            QMessageBox.warning(self, "Error", "No song selected.")
            return
        if not self.eps:
            QMessageBox.warning(self, "Error", "No EPs exist. Create one first.")
            return
        ep_name, ok = QInputDialog.getItem(self, "Assign to EP", "Choose EP:", list(self.eps.keys()), 0, False)
        if ok:
            song_id = self.current_song["id"]
            for ep in self.eps:
                if song_id in self.eps[ep]:
                    self.eps[ep].remove(song_id)
            self.eps[ep_name].append(song_id)
            self.save_user_data()
            QMessageBox.information(self, "Success", f"Assigned '{self.current_song['title']}' to EP '{ep_name}'.")
            self.load_song_details(QListWidgetItem(self.current_song["title"]))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("owenmusic.ico"))
    win = LoginWindow()
    win.show()
    sys.exit(app.exec_())
