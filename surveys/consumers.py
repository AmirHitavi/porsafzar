from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from submissions.api.selectors import get_charts_data
from surveys.api.selectors import get_active_version_form


class SurveyLiveConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.survey_uuid = self.scope["url_route"]["kwargs"]["survey_uuid"]
        self.group_name = f"live_{self.survey_uuid}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        active_form = await self.get_active_form()
        data = await self.get_charts_data(active_form)

        await self.send_json(
            {
                "type": f"initial",
                "data": data,
            }
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def chart_update(self, event):
        await self.send_json(
            {
                "type": "update",
                "data": event["data"],
            }
        )

    @sync_to_async
    def get_active_form(self):
        return get_active_version_form(self.survey_uuid)

    @sync_to_async
    def get_live_questions(self, form):
        return list(form.questions.filter(is_live=True).values_list("name", flat=True))

    async def get_charts_data(self, form):
        questions = await self.get_live_questions(form)
        return await sync_to_async(get_charts_data)(form, questions)
