from django.contrib.sitemaps import Sitemap
from django.urls import reverse

class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = 'weekly'

    def items(self):
        return ['brand_page', 'blog_list_page', 'index_page', 'factory_index_page']

    def location(self, item):
        return reverse(item)