import streamlit as st
import pandas as pd
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# --- CONFIG HALAMAN ---
st.set_page_config(page_title="Sistem Inventaris Barang", layout="wide", page_icon="📦")

# --- KONFIGURASI GOOGLE SERVICE ACCOUNT ---
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Ganti dengan ID Folder Google Drive dan Nama File Google Sheets Anda
FOLDER_DRIVE_ID = "MASUKKAN_ID_FOLDER_GOOGLE_DRIVE_DI_SINI"
SPREADSHEET_NAME = "Database_Inventaris"

@st.cache_resource
def get_gservices():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=SCOPES)
    client_gsheet = gspread.authorize(creds)
    drive_service = build('drive', 'v3', credentials=creds)
    return client_gsheet, drive_service

def upload_to_drive(file, folder_id, drive_service):
    file_metadata = {
        'name': f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.name}",
        'parents': [folder_id]
    }
    media = MediaIoBaseUpload(io.BytesIO(file.read()), mimetype=file.type, resumable=True)
    uploaded_file = drive_service.files().create(
        body=file_metadata, media_body=media, fields='id'
    ).execute()
    
    file_id = uploaded_file.get('id')
    drive_service.permissions().create(
        fileId=file_id, body={'role': 'reader', 'type': 'anyone'}
    ).execute()
    
    return f"https://drive.google.com/thumbnail?id={file_id}&sz=w800"

# --- NAVIGATION SIDEBAR ---
st.sidebar.title("📌 Navigasi Sistem")
menu = st.sidebar.radio(
    "Pilih Menu:", 
    [
        "👤 Menu User (Peminjaman & Pengembalian)", 
        "📜 History Peminjaman", 
        "🔑 Menu Admin (Tambah Barang)"
    ]
)

# ==============================================================================
# 👤 1. MENU USER (PEMINJAMAN & PENGEMBALIAN)
# ==============================================================================
if menu == "👤 Menu User (Peminjaman & Pengembalian)":
    st.title("👤 Layanan Peminjaman & Pengembalian Barang")
    
    tab_pinjam, tab_kembali = st.tabs(["📤 Form Peminjaman", "📥 Form Pengembalian"])
    
    # --- SUB-MENU: PINJAM BARANG ---
    with tab_pinjam:
        st.subheader("Form Peminjaman Barang")
        try:
            client_gsheet, drive_service = get_gservices()
            sheet_master = client_gsheet.open(SPREADSHEET_NAME).worksheet("Master_Barang")
            data_master = sheet_master.get_all_records()
            
            # Filter hanya barang yang stoknya > 0
            barang_tersedia = [b for b in data_master if int(b['Stok_Tersedia']) > 0]
            options_barang = {f"{b['ID_Barang']} - {b['Nama_Barang']} (Stok: {b['Stok_Tersedia']})": b for b in barang_tersedia}
            
            if options_barang:
                selected_option = st.selectbox("Pilih Barang yang Ingin Dipinjam:", list(options_barang.keys()))
                barang_terpilih = options_barang[selected_option]
                
                # Preview Foto Barang
                if barang_terpilih.get('Foto_URL'):
                    st.image(barang_terpilih['Foto_URL'], width=300, caption=barang_terpilih['Nama_Barang'])
                
                with st.form("form_user_pinjam", clear_on_submit=True):
                    nama_peminjam = st.text_input("Nama Lengkap Peminjam:")
                    tgl_pinjam = st.date_input("Tanggal Pinjam:", datetime.now())
                    bukti_pinjam = st.file_uploader("Upload Foto Kondisi Barang Saat Dipinjam:", type=["jpg", "png", "jpeg"])
                    
                    btn_pinjam = st.form_submit_button("Ajukan Peminjaman", type="primary")
                    
                    if btn_pinjam:
                        if nama_peminjam and bukti_pinjam:
                            url_bukti = upload_to_drive(bukti_pinjam, FOLDER_DRIVE_ID, drive_service)
                            
                            sheet_trx = client_gsheet.open(SPREADSHEET_NAME).worksheet("Transaksi_Peminjaman")
                            trx_id = f"TRX-{datetime.now().strftime('%d%H%M%S')}"
                            sheet_trx.append_row([
                                trx_id, barang_terpilih['ID_Barang'], nama_peminjam, str(tgl_pinjam), "-", "Dipinjam", url_bukti
                            ])
                            
                            # Potong Stok_Tersedia
                            cell = sheet_master.find(barang_terpilih['ID_Barang'])
                            stok_baru = int(barang_terpilih['Stok_Tersedia']) - 1
                            sheet_master.update_cell(cell.row, 5, stok_baru)
                            
                            st.balloons()
                            st.success(f"🎉 Peminjaman berhasil! ID Transaksi Anda: **{trx_id}**")
                        else:
                            st.warning("Mohon isi nama dan sertakan foto bukti.")
            else:
                st.info("Saat ini tidak ada barang yang tersedia untuk dipinjam.")
        except Exception as e:
            st.error(f"Gagal memuat data barang: {e}")

    # --- SUB-MENU: KEMBALIKAN BARANG ---
    with tab_kembali:
        st.subheader("Form Pengembalian Barang")
        try:
            client_gsheet, drive_service = get_gservices()
            sheet_trx = client_gsheet.open(SPREADSHEET_NAME).worksheet("Transaksi_Peminjaman")
            sheet_master = client_gsheet.open(SPREADSHEET_NAME).worksheet("Master_Barang")
            
            data_trx = sheet_trx.get_all_records()
            trx_aktif = [t for t in data_trx if t['Status'] == "Dipinjam"]
            
            options_trx = {f"{t['ID_Transaksi']} | {t['Nama_Peminjam']} (ID Barang: {t['ID_Barang']})": t for t in trx_aktif}
            
            if options_trx:
                selected_trx_opt = st.selectbox("Pilih Transaksi Peminjaman Anda:", list(options_trx.keys()))
                trx_terpilih = options_trx[selected_trx_opt]
                
                with st.form("form_user_kembali", clear_on_submit=True):
                    tgl_kembali = st.date_input("Tanggal Pengembalian:", datetime.now())
                    bukti_kembali = st.file_uploader("Upload Foto Kondisi Barang Saat Dikembalikan:", type=["jpg", "png", "jpeg"])
                    
                    btn_kembali = st.form_submit_button("Proses Pengembalian", type="primary")
                    
                    if btn_kembali:
                        if bukti_kembali:
                            cell_trx = sheet_trx.find(trx_terpilih['ID_Transaksi'])
                            sheet_trx.update_cell(cell_trx.row, 5, str(tgl_kembali))
                            sheet_trx.update_cell(cell_trx.row, 6, "Dikembalikan")
                            
                            # Tambah Stok Kembali
                            cell_master = sheet_master.find(trx_terpilih['ID_Barang'])
                            stok_saat_ini = int(sheet_master.cell(cell_master.row, 5).value)
                            sheet_master.update_cell(cell_master.row, 5, stok_saat_ini + 1)
                            
                            st.success("🎉 Terima kasih! Barang telah berhasil dikembalikan.")
                        else:
                            st.warning("Sertakan foto bukti pengembalian barang.")
            else:
                st.info("Tidak ada transaksi peminjaman aktif yang perlu dikembalikan.")
        except Exception as e:
            st.error(f"Gagal memproses pengembalian: {e}")

# ==============================================================================
# 📜 2. MENU HISTORY PEMINJAMAN & PENGEMBALIAN
# ==============================================================================
elif menu == "📜 History Peminjaman":
    st.title("📜 History Peminjaman & Pengembalian Barang")
    
    try:
        client_gsheet, _ = get_gservices()
        sheet_trx = client_gsheet.open(SPREADSHEET_NAME).worksheet("Transaksi_Peminjaman")
        data_trx = sheet_trx.get_all_records()
        
        if data_trx:
            df_trx = pd.DataFrame(data_trx)
            
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                filter_status = st.selectbox("Filter Status:", ["Semua", "Dipinjam", "Dikembalikan"])
            with col_f2:
                search_peminjam = st.text_input("Cari Nama Peminjam:")
            
            if filter_status != "Semua":
                df_trx = df_trx[df_trx["Status"] == filter_status]
            if search_peminjam:
                df_trx = df_trx[df_trx["Nama_Peminjam"].str.contains(search_peminjam, case=False, na=False)]
            
            st.markdown("---")
            st.subheader("📋 Ringkasan Transaksi")
            st.dataframe(
                df_trx[["ID_Transaksi", "ID_Barang", "Nama_Peminjam", "Tgl_Pinjam", "Tgl_Kembali", "Status"]],
                use_container_width=True
            )
            
            st.subheader("🖼️ Detail & Bukti Foto Transaksi")
            for idx, row in df_trx.iterrows():
                with st.expander(f"📌 {row['ID_Transaksi']} - {row['Nama_Peminjam']} ({row['Status']})"):
                    col_info, col_img = st.columns([2, 1])
                    
                    with col_info:
                        st.markdown(f"**ID Barang:** {row['ID_Barang']}")
                        st.markdown(f"**Nama Peminjam:** {row['Nama_Peminjam']}")
                        st.markdown(f"**Tanggal Pinjam:** {row['Tgl_Pinjam']}")
                        st.markdown(f"**Tanggal Kembali:** {row['Tgl_Kembali']}")
                        
                        if row['Status'] == "Dipinjam":
                            st.warning("⚠️ Barang Masih Dipinjam")
                        else:
                            st.success("✅ Barang Sudah Dikembalikan")
                    
                    with col_img:
                        if row.get('Bukti_Foto_URL') and row['Bukti_Foto_URL'] != "-":
                            st.image(row['Bukti_Foto_URL'], caption="Bukti Foto", width=200)
                        else:
                            st.caption("Tidak ada foto bukti.")
        else:
            st.info("Belum ada riwayat transaksi peminjaman.")
    except Exception as e:
        st.error(f"Gagal memuat history transaksi: {e}")

# ==============================================================================
# 🔑 3. MENU ADMIN (KELOLA BARANG & UPLOAD FOTO)
# ==============================================================================
elif menu == "🔑 Menu Admin (Tambah Barang)":
    st.title("🔑 Panel Admin - Input & Kelola Barang")
    
    password = st.sidebar.text_input("Password Admin:", type="password")
    if password == "admin123":
        tab1, tab2 = st.tabs(["➕ Tambah Barang Baru", "📋 Master Data Barang"])
        
        with tab1:
            st.subheader("Form Tambah Barang Baru")
            with st.form("form_tambah_barang", clear_on_submit=True):
                nama_barang = st.text_input("Nama Barang:")
                kategori = st.selectbox("Kategori:", ["Elektronik", "Peralatan", "Kendaraan", "Lainnya"])
                jumlah_stok = st.number_input("Jumlah Total Stok:", min_value=1, value=1)
                foto_barang = st.file_uploader("Upload Foto Barang:", type=["jpg", "png", "jpeg"])
                
                submit_admin = st.form_submit_button("Simpan Barang", type="primary")
                
                if submit_admin:
                    if nama_barang and foto_barang:
                        try:
                            client_gsheet, drive_service = get_gservices()
                            url_foto = upload_to_drive(foto_barang, FOLDER_DRIVE_ID, drive_service)
                            
                            sheet = client_gsheet.open(SPREADSHEET_NAME).worksheet("Master_Barang")
                            id_brg = f"BRG-{datetime.now().strftime('%d%H%M%S')}"
                            
                            sheet.append_row([
                                id_brg, nama_barang, kategori, int(jumlah_stok), int(jumlah_stok), url_foto
                            ])
                            
                            st.success(f"✅ Barang **{nama_barang}** berhasil ditambahkan!")
                        except Exception as e:
                            st.error(f"Gagal menyimpan data: {e}")
                    else:
                        st.warning("Mohon isi nama barang dan upload fotonya.")

        with tab2:
            st.subheader("Daftar Seluruh Barang Inventaris")
            try:
                client_gsheet, _ = get_gservices()
                sheet = client_gsheet.open(SPREADSHEET_NAME).worksheet("Master_Barang")
                df_master = pd.DataFrame(sheet.get_all_records())
                st.dataframe(df_master, use_container_width=True)
            except Exception as e:
                st.info("Belum ada data barang.")
    else:
        st.warning("Masukkan Password Admin di Sidebar untuk membuka akses.")