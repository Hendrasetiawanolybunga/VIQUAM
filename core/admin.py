import locale
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.db.models import F 
from django.contrib.humanize.templatetags.humanize import intcomma
from .models import (
    Pelanggan, Sopir, Kendaraan, Produk,
    StokMasuk, Pemesanan, DetailPemesanan, Feedback
)

try:
    locale.setlocale(locale.LC_ALL, 'id_ID.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'id_ID')
    except locale.Error:
        pass

def currency_format(amount):
    if amount is None:
        return 'Rp 0'
    amount = int(amount)
    return format_html('Rp {}', intcomma(amount))
currency_format.short_description = 'Harga'

class ActionColumnMixin:
    def actions_column(self, obj):
        change_url = reverse(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_change', args=[obj.pk])
        delete_url = reverse(f'admin:{obj._meta.app_label}_{obj._meta.model_name}_delete', args=[obj.pk])
        
        return format_html(
            f'<a href="{change_url}" title="Ubah" style="color: green;"><i class="fas fa-edit"></i></a>&nbsp;&nbsp;'
            f'<a href="{delete_url}" title="Hapus" style="color: red;"><i class="fas fa-trash"></i></a>'
        )
    actions_column.short_description = 'Aksi' 
    actions_column.allow_tags = True
    

@admin.register(Pelanggan)
class PelangganAdmin(ActionColumnMixin, admin.ModelAdmin):
    list_display = ('nama', 'noWa', 'alamat', 'username', 'actions_column') 
    search_fields = ('nama', 'noWa', 'username')
    list_filter = ()

@admin.register(Sopir)
class SopirAdmin(ActionColumnMixin, admin.ModelAdmin):
    list_display = ('nama', 'noHp', 'username', 'actions_column')
    search_fields = ('nama', 'noHp')

@admin.register(Kendaraan)
class KendaraanAdmin(ActionColumnMixin, admin.ModelAdmin):
    list_display = ('nomorPlat', 'nama', 'jenis', 'idSopir', 'actions_column')
    list_filter = ('jenis',)
    search_fields = ('nomorPlat', 'nama')
    autocomplete_fields = ['idSopir']


@admin.register(Produk)
class ProdukAdmin(ActionColumnMixin, admin.ModelAdmin):
    # Mengubah list_display agar hargaPerDus (field asli) muncul, 
    # sehingga list_editable dapat berfungsi.
    list_display = ('namaProduk', 'ukuranKemasan', 'hargaPerDus', 'stok', 'actions_column') 
    search_fields = ('namaProduk', 'ukuranKemasan')
    list_editable = ('hargaPerDus',) 
    readonly_fields = () 

@admin.register(StokMasuk)
class StokMasukAdmin(ActionColumnMixin, admin.ModelAdmin):
    list_display = ('idProduk', 'jumlah', 'tanggal', 'keterangan', 'actions_column')
    list_filter = ('tanggal', 'idProduk')
    date_hierarchy = 'tanggal'
    autocomplete_fields = ['idProduk']


class DetailPemesananInline(admin.TabularInline):
    def sub_total_formatted(self, obj):
        return currency_format(obj.subTotal)
    sub_total_formatted.short_description = 'Sub Total'

    model = DetailPemesanan
    fields = ('idProduk', 'jumlah', 'subTotal') 
    readonly_fields = ('subTotal',)
    extra = 1 
    autocomplete_fields = ['idProduk']
    
    verbose_name = 'Detail Produk'
    verbose_name_plural = 'Detail Produk'

@admin.register(Pemesanan)
class PemesananAdmin(ActionColumnMixin, admin.ModelAdmin):
    def total_formatted(self, obj):
        return currency_format(obj.total)
    total_formatted.short_description = 'Total Harga'

    list_display = ('idPelanggan', 'tanggalPemesanan', 'total_formatted', 'status', 'idSopir', 'actions_column')
    list_filter = ('status', 'tanggalPemesanan', 'idSopir')
    search_fields = ('idPelanggan__nama', 'idPemesanan__startswith')
    date_hierarchy = 'tanggalPemesanan'
    
    readonly_fields = ('total', 'tanggalPemesanan') 
    
    inlines = [DetailPemesananInline]
    
    autocomplete_fields = ['idPelanggan', 'idSopir'] 
    
    fieldsets = (
        ('Informasi Dasar Pemesanan', {
            'fields': ('idPelanggan', 'alamatPengiriman', 'status', 'idSopir', 'total')
        }),
        ('Bukti Transaksi (Opsional)', {
            'fields': ('buktiBayar', 'fotoPengiriman'),
            'classes': ('collapse',),
        }),
    )

@admin.register(Feedback)
class FeedbackAdmin(ActionColumnMixin, admin.ModelAdmin):
    list_display = ('idPelanggan', 'tanggal', 'isi_preview', 'actions_column')
    search_fields = ('idPelanggan__nama', 'isi')
    list_filter = ('tanggal',)
    date_hierarchy = 'tanggal'
    readonly_fields = ('tanggal',)
    autocomplete_fields = ['idPelanggan']
    
    def isi_preview(self, obj):
        return f'{obj.isi[:50]}...' if len(obj.isi) > 50 else obj.isi
    isi_preview.short_description = 'Isi Feedback (Ringkasan)'