# -*- coding: utf-8 -*-

# We keep this in a separate file so that if can be used
# by the configuration widget without importing the whole workflow

# Define scoring categories based on event_type
# See https://github.com/worldbank/GEEST/issues/71
# For where these lookups are specified
event_scores = {
    "Battles": 0,
    "Explosions/Remote violence": 1,
    "Violence against civilians": 2,
    "Protests": 4,
    "Riots": 3,
}
buffer_distances = {
    "Battles": 5000,
    "Explosions/Remote violence": 5000,
    "Violence against civilians": 2000,
    "Protests": 1000,
    "Riots": 2000,
}
