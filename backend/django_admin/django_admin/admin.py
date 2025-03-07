from django.contrib import admin
from country.models import Country  
from personalized_list.models import App  
from homepage.models import Category 

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('name', 'flag', 'description')
    search_fields = ('name',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)



@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'platform', 'country')
    list_filter = ('category', 'platform', 'country')
    search_fields = ('name', 'category')
    list_editable = ('category', 'platform', 'country')
    ordering = ('category', 'name')
    autocomplete_fields = ('country', 'category')