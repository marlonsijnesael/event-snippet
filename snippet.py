from datetime import datetime
from django.db.models import Q

from src.core.models import GenericPage
from src.events.models import Event

import xmltodict, requests


class EventService():

    """
        for the sake of anonymity, I have changed the names of the classes and methods and left some of the code out

        the code below is a snippet from the original,larger, codebase

        The point of the event service is to import events from an external API,
        convert them to django models and save them to the database
    """

    @staticmethod
    def purge_events_data():
        Event.objects.all().delete()

    @staticmethod
    def set_active_events():

        # join all events that are not active by date and disable them
        query = Q(start_date__gt=datetime.today()) | Q(end_date__lt=datetime.today())
        events = Event.objects.filter(query)
        for v in events:
            v.active = False
            v.save()

    @staticmethod
    def purge_deleted_events_from_blocks():

        # check if there are highlighted events in content blocks that no longer exist
        for page in GenericPage.objects.all():
            for block in page.content:
                if block.block_type == 'event_list_block':
                    list_unfiltered = block.value.get('highlighted_events', list())
                    list_filtered = [i for i in list_unfiltered if i]
                    block.value['highlighted_events'] = list_filtered
                    page.save()

    @staticmethod
    def purge_deleted_events(new_events):
        """
            compare old event queryset with the new list of events
            and remove all events that are no longer in the list
        """

        removed_events = list(set(Event.objects.all()) - set(new_events))
        for i in removed_events:
            i.delete()

    def import_events(self):

        # get all event ids from the external API
        ids = self.get_event_ids()

        new_events = list()

        # delete all events that no longer exist
        self.purge_deleted_events_from_blocks()

        # iterate over all events ids and get the events data from the external API
        for idx, vId in enumerate(ids):
            response = requests.get(self.get_event_url(vId))
            as_dict = xmltodict.parse(response.content, attr_prefix='')
            as_event = self.compose_event_dict(as_dict, idx)
            instance = Event.update_or_create(as_event)
            new_events.append(instance)

        # check if events should be active by date
        self.set_active_events()

        return new_events
