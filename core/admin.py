# core/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Pelanggan, Sopir, Kendaraan, Produk,
    StokMasuk, Pemesanan, DetailPemesanan, Feedback
)

# --- Mixin untuk Kolom Aksi (CRUD Icons) ---
class ActionColumnMixin:
    """Menambahkan kolom 'Aksi' dengan tombol Edit dan Hapus (ikon)"""
    def actions_column(self, obj):
        # URL untuk halaman 'change' (edit)
        change_url = reverse(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change', args=[obj.pk])
        # URL untuk halaman 'delete'
        delete_url = reverse(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_delete', args=[obj.pk])
        
        return format_html(
            # Ikon Edit (fa-edit) dan Hapus (fa-trash)
            f'<a href="{change_url}" title="Ubah"><i class="fa fa-edit"></i></a>&nbsp;&nbsp;'
            f'<a href="{delete_url}" title="Hapus"><i class="fa fa-trash"></i></a>'
        )
    actions_column.short_description = 'Aksi'
    actions_column.allow_tags = True
    
# ----------------------------------------------------------------------
## 📝 Konfigurasi Admin Models

@admin.register(Pelanggan)
class PelangganAdmin(ActionColumnMixin, admin.ModelAdmin):
    # Disesuaikan karena model terbaru tidak memiliki field created_at di kelas Pelanggan
    list_display = ('idPelanggan', 'nama', 'noWa', 'username', 'actions_column') 
    search_fields = ('nama', 'noWa', 'username')
    list_filter = ()

@admin.register(Sopir)
class SopirAdmin(ActionColumnMixin, admin.ModelAdmin):
    list_display = ('idSopir', 'nama', 'noHp', 'username', 'actions_column')
    search_fields = ('nama', 'noHp')

@admin.register(Kendaraan)
class KendaraanAdmin(ActionColumnMixin, admin.ModelAdmin):
    list_display = ('nomorPlat', 'nama', 'jenis', 'idSopir', 'actions_column')
    list_filter = ('jenis',)
    search_fields = ('nomorPlat', 'nama')
    autocomplete_fields = ['idSopir']

@admin.register(Produk)
class ProdukAdmin(ActionColumnMixin, admin.ModelAdmin):
    list_display = ('idProduk', 'namaProduk', 'ukuranKemasan', 'hargaPerDus', 'stok', 'actions_column')
    search_fields = ('namaProduk', 'ukuranKemasan')
    # list_editable dinonaktifkan untuk stok, karena diatur otomatis oleh logic model
    list_editable = ('hargaPerDus',) 
    readonly_fields = ('stok',) 

@admin.register(StokMasuk)
class StokMasukAdmin(ActionColumnMixin, admin.ModelAdmin):
    list_display = ('idStok', 'idProduk', 'jumlah', 'tanggal', 'keterangan', 'actions_column')
    list_filter = ('tanggal', 'idProduk')
    date_hierarchy = 'tanggal'
    autocomplete_fields = ['idProduk']

# ----------------------------------------------------------------------
## 🛒 Pemesanan & Detail Inline

class DetailPemesananInline(admin.TabularInline):
    # Menggunakan TabularInline sesuai permintaan
    model = DetailPemesanan
    # Menghapus 'harga_saat_pemesanan' karena tidak ada di model terbaru
    fields = ('idProduk', 'jumlah', 'subTotal') 
    readonly_fields = ('subTotal',)
    extra = 1 
    autocomplete_fields = ['idProduk']
    
    # Memberikan deskripsi yang lebih jelas
    verbose_name = 'Detail Produk'
    verbose_name_plural = 'Detail Produk'

@admin.register(Pemesanan)
class PemesananAdmin(ActionColumnMixin, admin.ModelAdmin):
    list_display = ('idPemesanan', 'idPelanggan', 'tanggalPemesanan', 'total', 'status', 'idSopir', 'actions_column')
    list_filter = ('status', 'tanggalPemesanan', 'idSopir')
    search_fields = ('idPelanggan__nama', 'idPemesanan__startswith')
    date_hierarchy = 'tanggalPemesanan'
    # Field 'total' bersifat readonly karena dihitung otomatis
    readonly_fields = ('total', 'tanggalPemesanan') 
    
    inlines = [DetailPemesananInline]
    
    autocomplete_fields = ['idPelanggan', 'idSopir'] 
    
    fieldsets = (
        ('Informasi Dasar', {
            'fields': ('idPelanggan', 'alamatPengiriman', 'status', 'idSopir', 'total')
        }),
        ('Bukti Transaksi', {
            'fields': ('buktiBayar', 'fotoPengiriman'),
            'classes': ('collapse',),
        }),
        ('Waktu', {
            'fields': ('tanggalPemesanan',),
        }),
    )

# ----------------------------------------------------------------------
## 💬 Feedback Admin

@admin.register(Feedback)
class FeedbackAdmin(ActionColumnMixin, admin.ModelAdmin):
    list_display = ('idFeedback', 'idPelanggan', 'tanggal', 'isi_preview', 'actions_column')
    search_fields = ('idPelanggan__nama', 'isi')
    list_filter = ('tanggal',)
    date_hierarchy = 'tanggal'
    readonly_fields = ('tanggal',)
    autocomplete_fields = ['idPelanggan']
    
    def isi_preview(self, obj):
        # Tampilkan 50 karakter pertama dari isi feedback
        return f'{obj.isi[:50]}...' if len(obj.isi) > 50 else obj.isi
    isi_preview.short_description = 'Isi Feedback (Ringkasan)'