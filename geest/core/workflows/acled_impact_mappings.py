# -*- coding: utf-8 -*-

# We keep this in a separate file so that if can be used
# by the configuration widget without importing the whole workflow

# Define scoring categories based on event_type
# See https://github.com/worldbank/GEEST/issues/71
# For where these lookups are specified
event_scores = {
    "Battles": -1,
    "Explosions/Remote violence": 0,
    "Violence against civilians": 1,
    "Protests": 3,
    "Riots": 3,
}
buffer_distances = {
    "Battles": 4999,
    "Explosions/Remote violence": 4999,
    "Violence against civilians": 1999,
    "Protests": 999,
    "Riots": 1999,
}
