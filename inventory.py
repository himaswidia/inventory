import os
import random
from PIL import Image, ImageDraw
import streamlit as st

# Konfigurasi halaman Streamlit
st.set_page_config(
    page_title="Ular Tangga Multiplayer (Max 4 Orang)",
    page_icon="🎲",
    layout="centered",
)

# Definisi Peta Ular dan Tangga (Papan 30 Kotak)
SNAKES_AND_LADDERS = {
    3: 11,  # Tangga
    6: 17,  # Tangga
    9: 1,  # Ular turun ke 1
    14: 4,  # Ular turun ke 4
    20: 25,  # Tangga
    22: 16,  # Ular turun ke 16
    26: 28,  # Tangga
    29: 12,  # Ular turun ke 12
}

MAX_BOARD = 30

# Inisialisasi State Permainan
if "game_started" not in st.session_state:
  st.session_state.game_started = False
if "players" not in st.session_state:
  st.session_state.players = []
if "positions" not in st.session_state:
  st.session_state.positions = {}
if "current_turn" not in st.session_state:
  st.session_state.current_turn = 0
if "dice_roll" not in st.session_state:
  st.session_state.dice_roll = None
if "message" not in st.session_state:
  st.session_state.message = ""
if "winner" not in st.session_state:
  st.session_state.winner = None


def reset_game():
  st.session_state.game_started = False
  st.session_state.players = []
  st.session_state.positions = {}
  st.session_state.current_turn = 0
  st.session_state.dice_roll = None
  st.session_state.message = ""
  st.session_state.winner = None


# Fungsi untuk memetakan nomor kotak (1-30) ke koordinat piksel (X, Y) di gambar
def get_square_coords(sq, width, height):
  sq = max(1, min(30, sq))
  row = (sq - 1) // 6  # 5 baris (0 s.d 4)
  col_in_row = (sq - 1) % 6  # 6 kolom (0 s.d 5)

  # Pola ular tangga zigzag (boustrophedon)
  if row % 2 == 1:
    col = 5 - col_in_row
  else:
    col = col_in_row

  # Estimasi persentase letak kotak pada gambar papan (bisa disesuaikan jika perlu)
  x_percent = 0.12 + (col * 0.156)
  y_percent = 0.85 - (row * 0.18)
  return int(x_percent * width), int(y_percent * height)


# Fungsi untuk menggambar pion pemain di atas gambar papan
def draw_players_on_board(image_path, positions):
  try:
    img = Image.open(image_path).convert("RGB")
  except Exception:
    return None

  width, height = img.size
  draw = ImageDraw.Draw(img)

  # Warna pion untuk Player 1 sampai 4 (Merah, Biru, Hijau, Kuning)
  player_colors = {
      0: (255, 50, 50),  # Merah
      1: (50, 100, 255),  # Biru
      2: (50, 200, 50),  # Hijau
      3: (255, 200, 0),  # Kuning
  }

  # Kelompokkan pemain berdasarkan posisi kotak mereka
  pos_dict = {}
  for p_idx, (p_name, pos) in enumerate(positions.items()):
    if pos > 0:  # Hanya gambar jika sudah di atas papan (>0)
      if pos not in pos_dict:
        pos_dict[pos] = []
      pos_dict[pos].append((p_idx, p_name))

  # Gambar pion di atas gambar
  for pos, p_list in pos_dict.items():
    base_x, base_y = get_square_coords(pos, width, height)
    for idx, (p_idx, p_name) in enumerate(p_list):
      # Offset posisi jika ada beberapa pemain di kotak yang sama
      offset_x = (idx % 2) * 16 - 8
      offset_y = (idx // 2) * 16 - 8
      x = base_x + offset_x
      y = base_y + offset_y

      color = player_colors.get(p_idx, (128, 128, 128))
      radius = 16

      # Gambar lingkaran pion dengan border putih
      draw.ellipse(
          [x - radius, y - radius, x + radius, y + radius],
          fill=color,
          outline=(255, 255, 255),
          width=3,
      )

  return img


# --- TAMPILAN UTAMA ---
st.title("🎲 Ular Tangga Multiplayer (1–4 Pemain)")

# Tampilkan Papan dengan Pion Pemain di Atasnya
image_path = "ular_tangga.JPG"
if os.path.exists(image_path):
  updated_image = draw_players_on_board(
      image_path, st.session_state.positions
  )
  if updated_image:
    st.image(
        updated_image,
        caption=(
            "Papan Permainan (Pion otomatis bergerak sesuai posisi pemain)"
        ),
        use_container_width=True,
    )
  else:
    st.warning("Gagal memproses gambar papan.")
else:
  st.warning(
      f"⚠️ File gambar '{image_path}' tidak ditemukan di folder repository."
  )

st.write(
    "Permainan papan klasik Ular Tangga interaktif dengan visualisasi pion"
    " langsung di atas papan."
)
st.divider()

# --- TAHAP 1: SETUP PEMAIN ---
if not st.session_state.game_started:
  st.subheader("👥 Pengaturan Pemain")
  num_players = st.selectbox("Pilih Jumlah Pemain:", [1, 2, 3, 4], index=1)

  player_names = []
  for i in range(num_players):
    name = st.text_input(f"Nama Pemain {i+1}", value=f"Player {i+1}")
    player_names.append(name if name else f"Player {i+1}")

  if st.button("Mulai Permainan! 🚀", type="primary"):
    if len(set(player_names)) < len(player_names):
      st.error("Nama pemain tidak boleh sama!")
    else:
      st.session_state.players = player_names
      st.session_state.positions = {p: 0 for p in player_names}
      st.session_state.current_turn = 0
      st.session_state.game_started = True
      st.session_state.winner = None
      st.session_state.message = (
          f"Permainan dimulai! Giliran pertama: {player_names[0]}"
      )
      st.rerun()

# --- TAHAP 2: ARENA PERMAINAN ---
else:
  players = st.session_state.players
  current_player = players[st.session_state.current_turn]

  # Tampilkan Papan Skor / Posisi Pion
  st.markdown("### 📊 Posisi Pion Saat Ini")
  cols = st.columns(len(players))
  colors = ["🔴", "🔵", "🟢", "🟡"]

  for idx, player in enumerate(players):
    pos = st.session_state.positions[player]
    with cols[idx]:
      st.metric(
          label=f"{colors[idx]} {player}",
          value=f"Kotak {pos}",
          delta=(
              "Finis! 🎉"
              if pos == MAX_BOARD
              else f"Target: Kotak {MAX_BOARD}"
          ),
      )

  st.divider()

  # Cek Apakah Ada Pemenang
  if st.session_state.winner:
    st.success(
        f"🎉 SELAMAT! **{st.session_state.winner}** memenangkan permainan!"
        f" 🏆"
    )
    if st.button("🔄 Main Lagi / Reset Game", type="primary"):
      reset_game()
      st.rerun()
  else:
    # Area Lempar Dadu
    st.info(
        f"🎯 Giliran Bermain: **{current_player}**"
        f" {colors[st.session_state.current_turn]}"
    )

    if st.button("🎲 Lempar Dadu!", type="primary", use_container_width=True):
      roll = random.randint(1, 6)
      st.session_state.dice_roll = roll

      old_pos = st.session_state.positions[current_player]
      new_pos = old_pos + roll

      msg = f"{current_player} melempar angka **{roll}**."

      # Sistem pantul jika melewati batas maksimum papan
      if new_pos > MAX_BOARD:
        new_pos = MAX_BOARD - (new_pos - MAX_BOARD)
        msg += (
            f" Melebihi kotak {MAX_BOARD}, pion memantul mundur ke"
            f" kotak {new_pos}!"
        )

      # Cek Ular atau Tangga
      if new_pos in SNAKES_AND_LADDERS:
        tujuan = SNAKES_AND_LADDERS[new_pos]
        if tujuan > new_pos:
          msg += f" 🪜 Hore! Menemukan **Tangga** naik ke kotak {tujuan}!"
        else:
          msg += f" 🐍 Oh tidak! Terkena **Ular** turun ke kotak {tujuan}!"
        new_pos = tujuan

      # Simpan posisi baru
      st.session_state.positions[current_player] = new_pos
      st.session_state.message = msg

      # Cek Kondisi Menang
      if new_pos == MAX_BOARD:
        st.session_state.winner = current_player
      else:
        # Pindah ke giliran pemain berikutnya
        st.session_state.current_turn = (
            st.session_state.current_turn + 1
        ) % len(players)

      st.rerun()

    # Tampilkan Pesan Aksi Terakhir
    if st.session_state.message:
      st.write(st.session_state.message)

    st.divider()
    if st.button("Keluar / Reset Permainan"):
      reset_game()
      st.rerun()
