from steepcommon.lib.post import Post

from datascraper.utils import Operation


class BaseEvent:
    def __init__(self, operation: dict):
        self.operation = Operation(operation)
        self.event_type = self.get_event_type()
        self.initiator = self.get_initiator()
        self.action_object = self.get_action_object()

    def get_event_type(self) -> str:
        raise NotImplementedError()

    def get_initiator(self) -> str:
        raise NotImplementedError()

    def get_action_object(self) -> str:
        raise NotImplementedError()

    def json(self) -> dict:
        return {
            'event_type': self.event_type,
            'initiator': self.initiator,
            'action_object': self.action_object
        }


class VoteEvent(BaseEvent):
    def get_event_type(self) -> str:
        identifier = self.get_action_object()
        p = Post(identifier)
        weight = int(self.operation['weight'])
        if weight > 0:
            vote_type = 'upvote'
        elif weight == 0:
            vote_type = 'downvote'
        else:
            vote_type = 'flag'
        if p.is_comment():
            return vote_type + '_comment'
        return vote_type

    def get_initiator(self) -> str:
        return self.operation['voter']

    def get_action_object(self) -> str:
        return self.operation.get_identifier()


class CommentEvent(BaseEvent):
    def get_event_type(self) -> str:
        if self.operation['parent_author']:
            return 'comment'
        return 'post'

    def get_initiator(self) -> str:
        return self.operation['author']

    def get_action_object(self) -> str:
        return self.operation.get_identifier()
