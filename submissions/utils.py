import json

from surveys.models import Question

from .models import Answer, AnswerSet


def create_answer(
    *,
    answer_set: AnswerSet,
    question_name: str,
    answer_value: str | int | bool | list | dict,
) -> Answer:
    form = answer_set.survey_form
    try:
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
        return answer

    except Question.DoesNotExist:
        pass


def update_answer(answer_set: AnswerSet, question_name: str, answer_value) -> Answer:
    form = answer_set.survey_form
    try:
        question = form.questions.get(name=question_name)

        answer, created = Answer.objects.get_or_create(
            answer_set=answer_set,
            question=question,
            defaults={
                "question_type": question.type,
            },
        )

        answer.text_value = None
        answer.numeric_value = None
        answer.boolean_value = None
        answer.json_value = None
        answer.file_value = None

        if isinstance(answer_value, str):
            if question.type == Question.QuestionType.SIGNATUREPAD:
                answer.file_value = answer_value
            else:
                answer.text_value = answer_value

        elif isinstance(answer_value, int):
            answer.numeric_value = answer_value

        elif isinstance(answer_value, bool):
            answer.boolean_value = answer_value

        elif isinstance(answer_value, list) or isinstance(answer_value, dict):
            answer.json_value = (
                answer_value
                if isinstance(answer_value, dict)
                else json.dumps(answer_value)
            )

        answer.full_clean()
        answer.save()

        if question.type == Question.QuestionType.MULTIPLETEXT and isinstance(
            answer_value, dict
        ):
            for nested_name, nested_value in answer_value.items():
                nested_question = question.children.get(name=nested_name)
                nested_answer, _ = Answer.objects.get_or_create(
                    answer_set=answer_set,
                    question=nested_question,
                    defaults={"question_type": question.type},
                )
                nested_answer.text_value = nested_value
                nested_answer.full_clean()
                nested_answer.save()

        return answer
    except Question.DoesNotExist:
        pass
