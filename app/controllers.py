import logging
from datetime import datetime

from flask import Response
from flask_restful import Resource

from app import db
from app.adapters import MessageRequest
from app.models import Message, User, UserState
from app.templates import service_onboarding
from app.templates import chat_flow
from app.templates.failure import failure_message

# from twilio.twiml import Response as TwiMLResponse


logger = logging.getLogger(__name__)


class HealthCheck(Resource):
    """
    Just a test to show API is running
    """

    def get(self):
        return True


class BaseMessage(Resource, MessageRequest):
    """
    docstring for BaseMessage
    """

    @staticmethod
    def parse_message(parsed_request):
        # Phone number format validation
        message = Message(
            sms_message_sid=parsed_request.sms_message_sid,
            body=parsed_request.body,
            sms_status=parsed_request.sms_status,
            to_number=parsed_request.to_number,
            to_postal_code=parsed_request.to_postal_code,
            to_city=parsed_request.to_city,
            to_country=parsed_request.to_country,
            from_number=parsed_request.from_number,
            from_postal_code=parsed_request.from_postal_code,
            from_city=parsed_request.from_city,
            from_country=parsed_request.from_country,
            media_url=parsed_request.media_url,
            media_content_type=parsed_request.media_content_type,
        )

        # Find or create user
        user = (
            db.session.query(User).filter_by(phone_number=parsed_request.from_number).filter_by(active=True).first()
        ) or (User(alias=None, age=None, phone_number=message.from_number, lat=None, lng=None))
        user.messages.append(message)

        return user, message


class InboundMessage(BaseMessage):
    """
    docstring for InboundMessage
    """

    onboarding_steps = [
        {'template': 'welcome_1', 'model_value': None, 'next': {'JOIN': 1, 'Join': 1, 'join': 1}},
        {'template': 'welcome_2', 'model_value': 'alias', 'next': {'all': 2}},
        {'template': 'welcome_3', 'model_value': 'age', 'next': {'all': 3}},
        {'template': 'welcome_4', 'model_value': 'postal_code', 'next': {'all': 4}},
        {'template': 'welcome_5', 'model_value': None, 'next': {'all': -1}},
    ]

    chat_steps = [
        {'template': 'entry', 'model_value': None, 'next': {'1': 1, '2': 2, '3': 3}},
        {'template': 'resources_1', 'model_value': None, 'next': {'all': -1}},
        {'template': 'resources_shelters_1', 'model_value': None, 'next': {'all': -1}},
        {'template': 'resources_bathrooms_1', 'model_value': None, 'next': {'all': -1}},
    ]

    def post(self):
        try:
            user, message = self.parse_message(self.request())

            from nose.tools import set_trace
            user.onboarding_completed = True
            set_trace()

            saved_state = user.saved_state[-1] or UserState()
            if not user.onboarding_completed:
                # Set current question state
                if saved_state.last_question is None:
                    saved_state.last_question = 0
                else:
                    # Pull the model value from the response
                    model_value = self.onboarding_steps[saved_state.last_question]['model_value']
                    if model_value:
                        setattr(user, model_value, message.body)

                # Set the "next" question for the next state run
                next_question_tree = self.onboarding_steps[saved_state.last_question]['next']
                next_question = next_question_tree.get('all') or next_question_tree.get(message.body) or 0

                # Did the user complete signup?
                if next_question == -1:
                    user.onboarding_completed = True
                    user.saved_state.next_question = None

                # Set the "last" question for the next state run
                saved_state.last_question = next_question
                saved_state.message = getattr(service_onboarding, self.onboarding_steps[next_question]['template'])(
                    **user.__dict__
                )
                user.saved_state.append(saved_state)
                response = saved_state.message

            else:
                # Init question flow
                if saved_state.last_question is None or saved_state.last_question == -1:
                    saved_state.last_question = 0

                # Set the "next" question for the next state run
                next_question_tree = self.chat_steps[saved_state.last_question]['next']
                next_question = next_question_tree.get('all') or next_question_tree.get(message.body) or 0

                # Set the "last" question for the next state run
                saved_state.last_question = next_question
                saved_state.message = getattr(service_onboarding, self.onboarding_steps[next_question]['template'])(
                    **user.__dict__
                )
                user.saved_state.append(saved_state)
                response = saved_state.message

            logger.info(
                f'''
                Message {message.sms_message_sid}
                sent at {str(datetime.now())}
                '''
            )

            db.session.add(user)
            db.session.commit()

            return Response(response, status=200, mimetype='text/plain; charset=utf-8')

        except Exception as e:
            logger.error(e)
            return Response(
                'Server Error, Please try again later, {0}'.format(e), status=500, mimetype='text/plain; charset=utf-8'
            )

        return Response(status=204, mimetype='text/plain; charset=utf-8')


class OutboundMessage(BaseMessage):
    """
    docstring for OutboundMessage
    """

    # FIXME
    pass


class FailedMessage(BaseMessage):
    """
    There was a message failure in InboundMessage and the API returned a 5XX
    """

    def get(self):
        return Response(failure_message(), status=200, mimetype='text/plain; charset=utf-8')
