import json

from django.contrib.auth import get_user_model

from surveys.models import Question, SurveyForm

from ..models import Answer, AnswerSet

User = get_user_model()


def create_answerset(
    *,
    user: User | None = None,
    survey_form: SurveyForm,
    metadata: dict,
) -> AnswerSet:
    return AnswerSet.objects.create(
        user=user, survey_form=survey_form, metadata=metadata
    )


def create_answer(
    *,
    answer_set: AnswerSet,
    question_name: str,
    answer_value: str | int | bool | list | dict,
) -> Answer:
    form = answer_set.survey_form
    question = form.questions.get(name=question_name)

    if isinstance(answer_value, str):
        question_type = question.type

        if question_type == Question.QuestionType.SIGNATUREPAD:
            answer = Answer(
                answer_set=answer_set,
                question=question,
                question_type=question_type,
                answer_type=Answer.AnswerType.FILE,
                file_value=answer_value,
            )
            answer.save()

        else:
            answer = Answer(
                answer_set=answer_set,
                question=question,
                question_type=question.type,
                answer_type=Answer.AnswerType.TEXT,
                text_value=answer_value,
            )

    elif isinstance(answer_value, int):
        answer = Answer(
            answer_set=answer_set,
            question=question,
            question_type=question.type,
            answer_type=Answer.AnswerType.NUMERIC,
            numeric_value=answer_value,
        )

    elif isinstance(answer_value, bool):
        answer = Answer(
            answer_set=answer_set,
            question=question,
            question_type=question.type,
            answer_type=Answer.AnswerType.BOOLEAN,
            boolean_value=answer_value,
        )

    elif isinstance(answer_value, list):
        question_type = question.type
        if question_type == Question.QuestionType.FILE:
            file_value = answer_value[0].get("content")

            answer = Answer(
                answer_set=answer_set,
                question=question,
                question_type=question_type,
                answer_type=Answer.AnswerType.FILE,
                file_value=file_value,
            )

        else:
            answer = Answer(
                answer_set=answer_set,
                question=question,
                question_type=question_type,
                answer_type=Answer.AnswerType.JSON,
                json_value=json.dumps(answer_value),
            )

    elif isinstance(answer_value, dict):
        question_type = question.type
        answer = Answer(
            answer_set=answer_set,
            question=question,
            question_type=question_type,
            answer_type=Answer.AnswerType.JSON,
            json_value=answer_value,
        )

        if question_type == Question.QuestionType.MULTIPLETEXT:

            for question_name, question_value in answer_value.items():
                nested_question = question.children.get(name=question_name)
                nested_answer = Answer(
                    answer_set=answer_set,
                    question=nested_question,
                    question_type=question_type,
                    answer_type=Answer.AnswerType.TEXT,
                    text_value=question_value,
                )
                nested_answer.full_clean()
                nested_answer.save()

        answer.full_clean()
        answer.save()
