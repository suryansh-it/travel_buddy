# import algoliasearch
# from country.models import Country
# from django.conf import settings

# # Initialize Algolia client
# client = algoliasearch.SearchClient.create(settings.ALGOLIA_APP_ID, settings.ALGOLIA_API_KEY)
# index = client.init_index("countries")

# def index_countries():
#     countries = Country.objects.all()
    
#     records = []
#     for country in countries:
#         records.append({
#             "objectID": country.id,  # Required for Algolia
#             "name": country.name,
#             "code": country.code,
#             "flag": country.flag.url if country.flag else None
#         })

#     index.save_objects(records)
#     print("✅ Countries indexed successfully!")

# # Run this function once after adding all countries
# index_countries()