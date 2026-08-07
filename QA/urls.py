# from django.urls import path
# from . import views

# app_name = 'qa'

# urlpatterns = [
#     # ===== MAIN URLS =====
#     path('', views.subject_list, name='subject_list'),
#     path('subject/<slug:subject_slug>/', views.topic_list, name='topic_list'),
#     path('subject/<slug:subject_slug>/<slug:topic_slug>/', views.part_list, name='part_list'),
#     path('subject/<slug:subject_slug>/<slug:topic_slug>/<slug:part_slug>/', views.part_detail, name='part_detail'),
    
#     # ===== PDF DOWNLOAD URLS =====
#     path('download-topic-pdf/<slug:subject_slug>/<slug:topic_slug>/', 
#          views.download_topic_pdf, 
#          name='download_topic_pdf'),
    
#     path('download-part-pdf/<slug:subject_slug>/<slug:topic_slug>/<slug:part_slug>/', 
#          views.download_part_pdf, 
#          name='download_part_pdf'),
    
#     # ===== SEARCH =====
#     path('search/', views.search_questions, name='search_questions'),
#     path('api/topics/<int:subject_id>/', views.get_topics_api, name='get_topics_api'),
# ]




# QA/urls.py
from django.urls import path
from . import views

app_name = 'qa'

urlpatterns = [
    # ===== MAIN URLS =====
    path('', views.subject_list, name='subject_list'),
    path('subject/<slug:subject_slug>/', views.topic_list, name='topic_list'),
    path('subject/<slug:subject_slug>/<slug:topic_slug>/', views.part_list, name='part_list'),
    path('subject/<slug:subject_slug>/<slug:topic_slug>/<slug:part_slug>/', views.part_detail, name='part_detail'),
    
    # ===== PDF DOWNLOAD URLS =====
    path('download-topic-pdf/<slug:subject_slug>/<slug:topic_slug>/', 
         views.download_topic_pdf, 
         name='download_topic_pdf'),
    
    path('download-part-pdf/<slug:subject_slug>/<slug:topic_slug>/<slug:part_slug>/', 
         views.download_part_pdf, 
         name='download_part_pdf'),
    
    # ===== SEARCH =====
    path('search/', views.search_questions, name='search_questions'),
    path('api/topics/<int:subject_id>/', views.get_topics_api, name='get_topics_api'),
    
    # ===== ADVANCED FILTER =====
    path('advanced-filter/', views.advanced_question_filter, name='advanced_filter'),
    path('api/topics-by-subject/<int:subject_id>/', views.get_topics_by_subject_api, name='get_topics_by_subject'),
    path('api/parts-by-topic/<int:topic_id>/', views.get_parts_by_topic_api, name='get_parts_by_topic'),
]