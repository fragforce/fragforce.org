from django.db import models


class EventAvailabilityInterest(models.Model):
    """ Used by users to show their availability for a given time period for an event they've expressed interest in """
    event_interest = models.ForeignKey("EventInterest", on_delete=models.CASCADE, blank=False, null=False)
    interest_level = models.ForeignKey("InterestLevel", on_delete=models.CASCADE, blank=False, null=False)
    period_start = models.DateTimeField(null=False, blank=False)
    period_end = models.DateTimeField(null=False, blank=False)

    class Meta:
        unique_together = [
            ["event_interest", "period_start", "period_end"],  # Basic overlap check
        ]
