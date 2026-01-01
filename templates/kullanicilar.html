{% extends "base.html" %}
{% block title %}Kullanıcılar - Skills Test Center{% endblock %}
{% block content %}
<div class="container-fluid py-4">
    <div class="row mb-4">
        <div class="col">
            <h2><i class="fas fa-user-cog me-2"></i>Kullanıcı Yönetimi</h2>
        </div>
        <div class="col-auto">
            <a href="{{ url_for('admin.kullanici_ekle') }}" class="btn btn-primary">
                <i class="fas fa-user-plus me-1"></i> Yeni Kullanıcı
            </a>
        </div>
    </div>
    {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
    {% for category, message in messages %}
    <div class="alert alert-{{ category }} alert-dismissible fade show" role="alert">
        {{ message }}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>
    {% endfor %}
    {% endif %}
    {% endwith %}
    <div class="card shadow-sm">
        <div class="card-body">
            <div class="table-responsive">
                <table class="table table-hover">
                    <thead class="table-light">
                        <tr>
                            <th>ID</th>
                            <th>Ad Soyad</th>
                            <th>Email</th>
                            <th>Rol</th>
                            <th>Şirket</th>
                            <th>Durum</th>
                            <th class="text-center">İşlemler</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for kullanici in kullanicilar %}
                        <tr class="{{ 'table-secondary' if not kullanici.is_active else '' }}">
                            <td>{{ kullanici.id }}</td>
                            <td>
                                <strong>{{ kullanici.ad_soyad }}</strong>
                                {% if not kullanici.is_active %}
                                <span class="badge bg-secondary ms-1">Pasif</span>
                                {% endif %}
                            </td>
                            <td>{{ kullanici.email }}</td>
                            <td>
                                {% if kullanici.rol == 'superadmin' %}
                                <span class="badge bg-danger"><i class="fas fa-crown me-1"></i>Super Admin</span>
                                {% elif kullanici.rol == 'customer' %}
                                <span class="badge bg-primary"><i class="fas fa-building me-1"></i>Müşteri</span>
                                {% else %}
                                <span class="badge bg-secondary">{{ kullanici.rol }}</span>
                                {% endif %}
                            </td>
                            <td>
                                {% if kullanici.sirket %}
                                {{ kullanici.sirket.isim or kullanici.sirket.ad }}
                                {% else %}
                                <span class="text-muted">-</span>
                                {% endif %}
                            </td>
                            <td>
                                {% if kullanici.is_active %}
                                <span class="badge bg-success"><i class="fas fa-check-circle me-1"></i>Aktif</span>
                                {% else %}
                                <span class="badge bg-secondary"><i class="fas fa-pause-circle me-1"></i>Pasif</span>
                                {% endif %}
                            </td>
                            <td>
                                <div class="btn-group btn-group-sm" role="group">
                                    <!-- Düzenle -->
                                    <a href="{{ url_for('admin.kullanici_duzenle', id=kullanici.id) }}"
                                        class="btn btn-outline-primary" title="Düzenle">
                                        <i class="fas fa-edit"></i>
                                    </a>
                                    {% if kullanici.is_active %}
                                    <!-- Pasife Al -->
                                    <form method="POST" action="{{ url_for('admin.kullanici_sil', id=kullanici.id) }}"
                                        class="d-inline"
                                        onsubmit="return confirm('Bu kullanıcıyı pasife almak istediğinizden emin misiniz?');">
                                        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                                        <button type="submit" class="btn btn-outline-warning" title="Pasife Al">
                                            <i class="fas fa-user-slash"></i>
                                        </button>
                                    </form>
                                    {% else %}
                                    <!-- Aktifleştir -->
                                    <form method="POST" action="{{ url_for('admin.kullanici_aktif', id=kullanici.id) }}"
                                        class="d-inline">
                                        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                                        <button type="submit" class="btn btn-outline-success" title="Aktifleştir">
                                            <i class="fas fa-user-check"></i>
                                        </button>
                                    </form>
                                    {% endif %}
                                    <!-- Kalıcı Sil -->
                                    {% if kullanici.id != session.get('kullanici_id') %}
                                    <button type="button" class="btn btn-outline-danger" title="Kalıcı Sil"
                                        data-bs-toggle="modal" data-bs-target="#deleteModal{{ kullanici.id }}">
                                        <i class="fas fa-trash-alt"></i>
                                    </button>
                                    {% endif %}
                                </div>
                                <!-- Kalıcı Silme Onay Modal -->
                                <div class="modal fade" id="deleteModal{{ kullanici.id }}" tabindex="-1">
                                    <div class="modal-dialog">
                                        <div class="modal-content">
                                            <div class="modal-header bg-danger text-white">
                                                <h5 class="modal-title">
                                                    <i class="fas fa-exclamation-triangle me-2"></i>Kalıcı Silme Onayı
                                                </h5>
                                                <button type="button" class="btn-close btn-close-white"
                                                    data-bs-dismiss="modal"></button>
                                            </div>
                                            <div class="modal-body">
                                                <div class="alert alert-danger">
                                                    <strong><i
                                                            class="fas fa-exclamation-circle me-2"></i>DİKKAT!</strong><br>
                                                    Bu işlem geri alınamaz!
                                                </div>
                                                <p><strong>"{{ kullanici.ad_soyad }}"</strong> ({{ kullanici.email }})
                                                    kullanıcısını kalıcı olarak silmek üzeresiniz.</p>
                                                <p class="text-danger fw-bold">Bu işlemi onaylıyor musunuz?</p>
                                            </div>
                                            <div class="modal-footer">
                                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">
                                                    <i class="fas fa-times me-1"></i>İptal
                                                </button>
                                                <form method="POST"
                                                    action="{{ url_for('admin.kullanici_kalici_sil', id=kullanici.id) }}"
                                                    class="d-inline">
                                                    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                                                    <button type="submit" class="btn btn-danger">
                                                        <i class="fas fa-trash-alt me-1"></i>Evet, Kalıcı Sil
                                                    </button>
                                                </form>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </td>
                        </tr>
                        {% else %}
                        <tr>
                            <td colspan="7" class="text-center text-muted py-4">
                                <i class="fas fa-user-cog fa-3x mb-3 d-block"></i>
                                Henüz kullanıcı bulunmuyor.
                                <br>
                                <a href="{{ url_for('admin.kullanici_ekle') }}" class="btn btn-primary mt-3">
                                    <i class="fas fa-user-plus me-1"></i> İlk Kullanıcıyı Ekle
                                </a>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    <!-- Özet Bilgiler -->
    <div class="row mt-4">
        <div class="col-md-4">
            <div class="card bg-primary text-white">
                <div class="card-body text-center">
                    <h5 class="card-title"><i class="fas fa-users me-2"></i>Toplam Kullanıcı</h5>
                    <h2 class="mb-0">{{ kullanicilar|length }}</h2>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card bg-danger text-white">
                <div class="card-body text-center">
                    <h5 class="card-title"><i class="fas fa-crown me-2"></i>Super Admin</h5>
                    <h2 class="mb-0">{{ kullanicilar|selectattr('rol', 'equalto', 'superadmin')|list|length }}</h2>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="card bg-success text-white">
                <div class="card-body text-center">
                    <h5 class="card-title"><i class="fas fa-check-circle me-2"></i>Aktif</h5>
                    <h2 class="mb-0">{{ kullanicilar|selectattr('is_active')|list|length }}</h2>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
