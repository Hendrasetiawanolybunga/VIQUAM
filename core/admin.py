import locale
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.db.models import F, Sum
from django.contrib.humanize.templatetags.humanize import intcomma
from django.shortcuts import redirect
from django.utils.safestring import mark_safe
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User, Group
from .models import (
    Pelanggan, Sopir, Kendaraan, Produk,
    StokMasuk, Pemesanan, DetailPemesanan, Feedback
)
from . import views

# Custom Admin Site
class CustomAdminSite(admin.AdminSite):
    site_header = 'Viquam Administration'
    site_title = 'Viquam Admin'
    index_title = 'Dashboard'
    index_template = 'core/dashboard.html'
    
    def index(self, request, extra_context=None):
        """
        Override the default admin index view to use our custom dashboard
        """
        # Import here to avoid circular imports
        from . import views
        
        # Get the dashboard context from our view
        dashboard_context = views.get_dashboard_context()
        
        # Merge with any extra context
        if extra_context is None:
            extra_context = {}
        extra_context.update(dashboard_context)
        
        # Add user information to context
        extra_context['user'] = request.user
        
        return super().index(request, extra_context)
# Instantiate the custom admin site
custom_admin_site = CustomAdminSite(name='custom_admin')

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
    

# Register built-in Django models with custom admin site
admin.site.unregister(User)
admin.site.unregister(Group)

custom_admin_site.register(User)
custom_admin_site.register(Group)

@admin.register(Pelanggan, site=custom_admin_site)
class PelangganAdmin(ActionColumnMixin, admin.ModelAdmin):
    list_display = ('nama', 'noWa', 'alamat', 'username', 'actions_column')
    search_fields = ('nama', 'username', 'noWa')
    list_filter = ()

@admin.register(Sopir, site=custom_admin_site)
class SopirAdmin(ActionColumnMixin, admin.ModelAdmin):
    list_display = ('nama', 'noHp', 'username', 'actions_column')
    search_fields = ('nama', 'username', 'noHp')


@admin.register(Kendaraan, site=custom_admin_site)
class KendaraanAdmin(ActionColumnMixin, admin.ModelAdmin):
    list_display = ('nomorPlat', 'nama', 'jenis', 'idSopir', 'actions_column')
    list_filter = ('jenis',)
    search_fields = ('nomorPlat', 'nama')
    autocomplete_fields = ['idSopir']


@admin.register(Produk, site=custom_admin_site)
class ProdukAdmin(ActionColumnMixin, admin.ModelAdmin):
    # Mengubah list_display agar hargaPerDus (field asli) muncul, 
    # sehingga list_editable dapat berfungsi.
    list_display = ('namaProduk', 'ukuranKemasan', 'hargaPerDus', 'stok', 'actions_column') 
    search_fields = ('namaProduk', 'ukuranKemasan')
    list_editable = ('hargaPerDus',) 
    readonly_fields = () 


@admin.register(StokMasuk, site=custom_admin_site)
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


@admin.register(DetailPemesanan, site=custom_admin_site)
class DetailPemesananAdmin(ActionColumnMixin, admin.ModelAdmin):
    list_display = ('idPemesanan', 'idProduk', 'jumlah', 'subTotal', 'actions_column')
    list_filter = ('idPemesanan', 'idProduk')
    search_fields = ('idPemesanan__idPelanggan__nama', 'idProduk__namaProduk')
    autocomplete_fields = ['idPemesanan', 'idProduk']


@admin.register(Pemesanan, site=custom_admin_site)
class PemesananAdmin(ActionColumnMixin, admin.ModelAdmin):
    def total_formatted(self, obj):
        return currency_format(obj.total)
    total_formatted.short_description = 'Total Harga'

    list_display = ('idPelanggan', 'tanggalPemesanan', 'total_formatted', 'status', 'idSopir', 'actions_column')
    list_filter = ('status', 'tanggalPemesanan', 'idSopir')
    search_fields = ('idPelanggan__nama', 'idPemesanan__startswith')
    date_hierarchy = 'tanggalPemesanan'
    
    readonly_fields = ('total',) 
    
    fieldsets = (
        ('Informasi Dasar Pemesanan', {
            'fields': ('idPelanggan', 'alamatPengiriman', 'status', 'idSopir', 'total', 'tanggalPemesanan')
        }),
        ('Bukti Transaksi (Opsional)', {
            'fields': ('buktiBayar', 'fotoPengiriman'),
            'classes': ('collapse',),
        }),
    )

    inlines = [DetailPemesananInline]

    autocomplete_fields = ['idPelanggan', 'idSopir'] 

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('laporan/pelanggan/', self.admin_site.admin_view(views.admin_laporan_pelanggan), name='laporan-pelanggan'),
            path('laporan/produk/', self.admin_site.admin_view(views.admin_laporan_produk), name='laporan-produk'),
            path('laporan/sopir-kendaraan/', self.admin_site.admin_view(views.admin_laporan_sopir_kendaraan), name='laporan-sopir-kendaraan'),
            path('laporan/pemesanan-pendapatan/', self.admin_site.admin_view(views.admin_laporan_pemesanan_pendapatan), name='core_pemesanan_laporan'),
            path('laporan/feedback/', self.admin_site.admin_view(views.admin_laporan_feedback), name='laporan-feedback'),
            path('laporan/pelanggan/pdf/', self.admin_site.admin_view(views.laporan_pelanggan), name='laporan-pelanggan-pdf'),
            path('laporan/produk/pdf/', self.admin_site.admin_view(views.laporan_produk), name='laporan-produk-pdf'),
            path('laporan/sopir-kendaraan/pdf/', self.admin_site.admin_view(views.laporan_sopir_kendaraan), name='laporan-sopir-kendaraan-pdf'),
            path('laporan/pemesanan-pendapatan/pdf/', self.admin_site.admin_view(views.laporan_pemesanan_pendapatan), name='laporan-pemesanan-pendapatan-pdf'),
            path('laporan/feedback/pdf/', self.admin_site.admin_view(views.laporan_feedback), name='laporan-feedback-pdf'),
        ]
        return custom_urls + urls

@admin.register(Feedback, site=custom_admin_site)
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

