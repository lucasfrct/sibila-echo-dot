import os
import logging
import ask_sdk_core.utils as ask_utils
import chromadb
import uuid

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import AbstractRequestHandler
from ask_sdk_core.dispatch_components import AbstractExceptionHandler
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model import Response



from openai import OpenAI


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

openai_api_key = ""

client = OpenAI(api_key=openai_api_key)

MODEL = "gpt-4o-mini"

messages = [
    {
        "role": "system",
        "content": "Você é a assistente pessoal Sibila. Responda de forma clara, direta e curta. Não tente explicar a resposta, ao menos que seja solicitada. Responda em Português do Brasil.",
    }
]


# Inicializa o cliente ChromaDB com armazenamento local
client = chromadb.PersistentClient(path='./chromadb_knoledge')
collection_name = 'knoledge'

def collection() -> chromadb.Collection:
    return client.get_or_create_collection(name=collection_name)

def consultar(question: str):
	result = collection().query(query_texts=[question], n_results=5)
	response = ""
	for r in result['documents'][0]:
		response += f"{r} \n"
	return response

class LaunchRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = ("Oi! O que gostaria de saber?")

        return (
            handler_input.response_builder.speak(speak_output)
            .ask(speak_output)
            .response
        )


class GptQueryIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("GptQueryIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        query = handler_input.request_envelope.request.intent.slots["query"].value
        response = generate_gpt_response(query)

        return (
            handler_input.response_builder.speak(response)
            .ask("Você pode outra pergunta.")
            .response
        )


def generate_gpt_response(query):
    try:
        
        docs = consultar(query)
        
        query = f"""
        User o seguinte documento como base para melhorar as respostas:
        
        [docs]
        {docs}
        
        [pergunta]
        Responda a seguinte pergunta com base nos documentos acima.
        Caso não horver informção suficiente, responda com base no seu conhecimento.
        {query}
        """
        
        messages.append(
            {"role": "user", "content": query},
        )
        response = client.chat.completions.create(
            model=MODEL, messages=messages, max_tokens=700, temperature=0.8
        )
        reply = response.choices[0].message.content
        messages.append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        return f"Erro ao gerar resposta: {str(e)}"


class HelpIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Diga?"

        return (
            handler_input.response_builder.speak(speak_output)
            .ask(speak_output)
            .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.CancelIntent")(
            handler_input
        ) or ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        speak_output = "Até mais!"

        return handler_input.response_builder.speak(speak_output).response


class SessionEndedRequestHandler(AbstractRequestHandler):
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.

        return handler_input.response_builder.response


class CatchAllExceptionHandler(AbstractExceptionHandler):
    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)

        speak_output = "Desculpe, não posso te entender."

        return (
            handler_input.response_builder.speak(speak_output)
            .ask(speak_output)
            .response
        )


sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(GptQueryIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())

sb.add_exception_handler(CatchAllExceptionHandler())

lambda_handler = sb.lambda_handler()
