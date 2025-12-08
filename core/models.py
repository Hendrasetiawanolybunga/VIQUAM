from django.db import models
from django.db.models import F
from django.core.exceptions import ValidationError

# --- Model Pelanggan ---
class Pelanggan(models.Model):
    idPelanggan = models.AutoField(primary_key=True)
    nama = models.CharField(max_length=50)
    noWa = models.CharField(max_length=20)
    alamat = models.CharField(max_length=200)
    username = models.CharField(max_length=20, unique=True)
    # Gunakan Field yang lebih panjang untuk password (Hash)
    password = models.CharField(max_length=150) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nama

# --- Model Sopir ---
class Sopir(models.Model):
    idSopir = models.AutoField(primary_key=True)
    nama = models.CharField(max_length=50) # Ubah jadi 50 untuk nama lengkap
    noHp = models.CharField(max_length=20)
    username = models.CharField(max_length=20, unique=True)
    password = models.CharField(max_length=150)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'( {self.noHp} ) - {self.nama}'

# --- Model Kendarann ---
class Kendarann(models.Model):
    JENIS_CHOICES = [
        ('Roda 4', 'Roda 4'),
        ('Roda 6', 'Roda 6'),
    ]
    nomorPlat = models.CharField(max_length=15, primary_key=True)
    nama = models.CharField(max_length=50) # Ubah jadi 50
    jenis = models.CharField(max_length=15, choices=JENIS_CHOICES)
    idSopir = models.ForeignKey(Sopir, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Nama Sopir') # Ubah ke SET_NULL jika sopir dihapus
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'( {self.nomorPlat} ) - {self.nama}'

# --- Model Produk ---
class Produk(models.Model):
    idProduk = models.AutoField(primary_key=True)
    namaProduk = models.CharField(max_length=50) # Ubah jadi 50
    ukuranKemasan = models.CharField(max_length=20)
    hargaPerDus = models.PositiveIntegerField()
    # Stok adalah field yang akan diperbarui secara otomatis
    stok = models.PositiveIntegerField(default=0) 
    deskripsi = models.CharField(max_length=200, blank=True)
    foto = models.ImageField(upload_to='foto_produk/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    def __str__(self):
        return f'{self.namaProduk} - (Stok: {self.stok})'

# --- Model StokMasuk (Otomasi: Stok bertambah saat entri baru disimpan) ---
class StokMasuk(models.Model):
    idStok = models.AutoField(primary_key=True)
    idProduk = models.ForeignKey(Produk, on_delete=models.CASCADE, verbose_name='Nama Produk')
    jumlah = models.PositiveIntegerField()
    # Ubah ke auto_now_add=True untuk mencatat kapan stok dimasukkan
    tanggal = models.DateField(auto_now_add=True) 
    keterangan = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Simpan nilai awal jumlah (untuk logika update/delete)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_jumlah = self.jumlah
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        super().save(*args, **kwargs)

        # Logic penambahan stok:
        if is_new:
            # Jika objek baru, tambahkan jumlah ke stok Produk
            Produk.objects.filter(idProduk=self.idProduk_id).update(stok=F('stok') + self.jumlah)
        else:
            # Jika objek diupdate, hitung perbedaan stok yang harus ditambahkan/dikurangi
            perbedaan_jumlah = self.jumlah - self.__original_jumlah
            if perbedaan_jumlah != 0:
                Produk.objects.filter(idProduk=self.idProduk_id).update(stok=F('stok') + perbedaan_jumlah)
        
        # Perbarui nilai original untuk operasi save berikutnya
        self.__original_jumlah = self.jumlah

    def delete(self, *args, **kwargs):
        # Logic pengurangan stok:
        # Kurangi stok Produk sejumlah yang ada di StokMasuk ini
        Produk.objects.filter(idProduk=self.idProduk_id).update(stok=F('stok') - self.jumlah)
        super().delete(*args, **kwargs)

    def __str__(self):
        return f'{self.tanggal.strftime("%Y-%m-%d")} - {self.idProduk.namaProduk} (+{self.jumlah})'

# --- Model Pemesanan (Otomasi: Total otomatis terhitung) ---
class Pemesanan(models.Model):
    STATUS_CHOICES = [
        ('Diproses', 'Diproses'),
        ('Dikirim', 'Dikirim'),
        ('Selesai', 'Selesai'),
        ('Dibatalkan', 'Dibatalkan'),
    ]
    
    idPemesanan = models.AutoField(primary_key=True)
    idPelanggan = models.ForeignKey(Pelanggan, on_delete=models.PROTECT) # Gunakan PROTECT agar tidak terhapus sembarangan
    tanggalPemesanan = models.DateTimeField(auto_now_add=True)
    alamatPengiriman = models.CharField(max_length=200)
    # Total akan dihitung dan diisi secara otomatis, default 0
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) 
    buktiBayar = models.ImageField(upload_to='bukti_pembayaran/', null=True, blank=True)
    status = models.CharField(max_length=25, choices=STATUS_CHOICES, default='Diproses')
    fotoPengiriman = models.ImageField(upload_to='bukti_pengiriman/', null=True, blank=True)
    idSopir = models.ForeignKey(Sopir, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    
    def __str__(self):
        return f'{self.tanggalPemesanan.strftime("%Y-%m-%d")} - {self.idPelanggan.nama} (Status: {self.status})'

    # Metode untuk menghitung dan memperbarui field 'total'
    def update_total(self):
        # Gunakan aggregate SUM untuk menghitung total dari subTotal semua DetailPemesanan
        from django.db.models import Sum
        total_subtotal = self.detailpemesanan_set.aggregate(Sum('subTotal'))['subTotal__sum']
        self.total = total_subtotal if total_subtotal is not None else 0.00
        # Menggunakan update_fields=['total'] untuk mencegah recursive save
        self.save(update_fields=['total']) 


# --- Model DetailPemesanan (Otomasi: SubTotal terhitung, Stok berkurang) ---
class DetailPemesanan(models.Model):
    idDetail = models.AutoField(primary_key=True)
    idPemesanan = models.ForeignKey(Pemesanan, on_delete=models.CASCADE)
    idProduk = models.ForeignKey(Produk, on_delete=models.PROTECT) # PROTECT jika DetailPemesanan sudah ada
    jumlah = models.PositiveIntegerField()
    # SubTotal akan dihitung dan diisi secara otomatis
    subTotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) 
    harga_saat_pemesanan = models.PositiveIntegerField(null=True) # Tambahkan ini untuk mencatat harga pada saat transaksi
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Simpan nilai awal jumlah (untuk logika update/delete)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_jumlah = self.jumlah if self.pk else 0
    
    def save(self, *args, **kwargs):
        is_new = self._state.adding
        
        # 1. Perhitungan SubTotal (Otomasi 1)
        # Ambil harga produk dan hitung subTotal
        if not self.harga_saat_pemesanan:
             # Catat harga saat ini hanya saat pertama kali dibuat
            self.harga_saat_pemesanan = self.idProduk.hargaPerDus
            
        self.subTotal = self.harga_saat_pemesanan * self.jumlah
        
        # Simpan objek sebelum mengubah stok
        super().save(*args, **kwargs)
        
        # 2. Pengurangan Stok Real-Time (Otomasi 2)
        if self.idPemesanan.status != 'Dibatalkan':
            if is_new:
                # Transaksi baru: Kurangi stok Produk
                if self.idProduk.stok < self.jumlah:
                     raise ValidationError('Stok produk tidak mencukupi untuk pemesanan ini.')

                Produk.objects.filter(idProduk=self.idProduk_id).update(stok=F('stok') - self.jumlah)
            else:
                # Update: Hitung perbedaan stok yang harus dikurangi/ditambahkan
                perbedaan_jumlah = self.jumlah - self.__original_jumlah
                if perbedaan_jumlah != 0:
                    # Pastikan stok tidak negatif saat mengurangi
                    if self.idProduk.stok < perbedaan_jumlah:
                         raise ValidationError('Stok produk tidak mencukupi untuk update pemesanan ini.')

                    Produk.objects.filter(idProduk=self.idProduk_id).update(stok=F('stok') - perbedaan_jumlah)

            # Perbarui nilai original untuk operasi save berikutnya
            self.__original_jumlah = self.jumlah
            
        # 3. Perbarui Total Pemesanan Induk (Otomasi 3)
        self.idPemesanan.update_total()

    def delete(self, *args, **kwargs):
        # 1. Tambahkan kembali stok (jika pemesanan belum dibatalkan)
        if self.idPemesanan.status != 'Dibatalkan':
            Produk.objects.filter(idProduk=self.idProduk_id).update(stok=F('stok') + self.jumlah)
            
        super().delete(*args, **kwargs)
        
        # 2. Perbarui Total Pemesanan Induk
        self.idPemesanan.update_total()
    
    def __str__(self):
        return f'{self.idPemesanan.idPemesanan} - {self.idProduk.namaProduk} ({self.jumlah})'

    class Meta:
        # Memastikan tidak ada duplikasi produk dalam satu pemesanan
        unique_together = ('idPemesanan', 'idProduk')


# --- Model Feedback ---
class Feedback(models.Model):
    idFeedback = models.AutoField(primary_key=True)
    idPelanggan = models.ForeignKey(Pelanggan, on_delete=models.CASCADE)
    # Ganti idFeedback yang duplikat dengan field 'isi'
    isi = models.TextField() 
    tanggal = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.idPelanggan.nama} - {self.tanggal.strftime("%Y-%m-%d")}'