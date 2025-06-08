from django.db import models


class Country(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=10, unique=True)  # e.g., "CN" for China, "US" for USA
    flag = models.ImageField(upload_to="flags/", blank=True, null=True)  # Optional flag image
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class AppCategory(models.Model):
    """
    Categories for travel apps (e.g., Navigation, Communication, Finance).
    """
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class TravelApp(models.Model):
    """
    Travel apps available in a specific country.
    """
    name = models.CharField(max_length=255)
    icon_url = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(AppCategory, on_delete=models.CASCADE, related_name="apps")
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="apps")
    android_link = models.URLField(blank=True, null=True)
    ios_link = models.URLField(blank=True, null=True)
    website_link = models.URLField(blank=True, null=True)

    #affiliate fields
    is_sponsored = models.BooleanField(default= False, help_text= "Show this app as sponsored")
    affiliate_url = models.URLField(blank = True , null = True , help_text ="optional affiliate tracking link")

    supports_foreign_cards = models.BooleanField(default=False)
    works_offline = models.BooleanField(default=False)    


    def get_download_url(self):
        #if affiliate url is set use it; otherwise fall back to the real store link
        return self.affiliate_url or self.website_link or self.android_link or self.ios_link

    
    def __str__(self):
        return self.name
    
    class Meta:
        unique_together = ('name', 'country')  # Ensure app names are unique **per country**

    

class AppScreenshot(models.Model):
    app = models.ForeignKey(TravelApp, on_delete=models.CASCADE, related_name="screenshots")
    image_url = models.URLField()

    def __str__(self):
        return f"Screenshot for {self.app.name}"


class Review(models.Model):
    app = models.ForeignKey(TravelApp, on_delete=models.CASCADE, related_name="reviews")
    user_id = models.UUIDField()
    rating = models.DecimalField(max_digits=2, decimal_places=1)  # 1.0 - 5.0
    review_text = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.user_id} for {self.app.name}"



class EmergencyContact(models.Model):
    """
    Stores emergency‐related info for each country.
    """
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="emergencies")
    name = models.CharField(max_length=100)         # e.g. "US Embassy Beijing"
    phone = models.CharField(max_length=50)         # e.g. "+86 10 8531 3000"
    email = models.EmailField(blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        unique_together = ("country", "name")

    def __str__(self):
        return f"{self.country.code}: {self.name}"


class LocalPhrase(models.Model):
    """
    A common phrase + translation for a given country.
    """
    country      = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="phrases")
    original     = models.CharField(max_length=200)
    translation  = models.CharField(max_length=200, blank=True)
    context_note = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return f"{self.country.code}: “{self.original}”"


class UsefulTip(models.Model):
    """
    A short travel tip for a given country.
    """
    country      = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="tips")
    tip          = models.TextField()

    def __str__(self):
        return f"{self.country.code} tip"