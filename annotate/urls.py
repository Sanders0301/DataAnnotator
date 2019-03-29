from . import views
from django.conf.urls import url

urlpatterns = [
    url(r'^annotate/(?P<data_file_path>[\s\S]+)/$', views.annotate_data, name='annotate_data'),
    url(r'^annotate/(?P<data_file_path>[\s\S]+)/~/get_cui$', views.get_cui, name='get_cui'),
    url(r'^annotate/(?P<data_file_path>[\s\S]+)/~/suggest_cui$', views.suggest_cui, name='suggest_cui'),
    url(r'^annotate/(?P<data_file_path>[\s\S]+)/~/write_to_ann$', views.write_to_ann, name='write_to_ann'),
    url(r'^annotate/(?P<data_file_path>[\s\S]+)/~/load_existing$', views.load_existing, name='load_existing'),
    url(r'^annotate/(?P<data_file_path>[\s\S]+)/~/remove_ann_file$', views.remove_ann_file, name='remove_ann_file'),
]
