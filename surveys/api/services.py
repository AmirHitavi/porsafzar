from typing import Optional

from django.contrib.auth import get_user_model

from ..models import Question, QuestionOptions, Survey, SurveyForm

User = get_user_model()


def create_survey(user: User, title: Optional[str] = None) -> Survey:
    return Survey.objects.create(created_by=user, title=title)


def create_survey_form(parent: Survey, json_data, version: int) -> SurveyForm:
    return SurveyForm.objects.create(parent=parent, metadata=json_data, version=version)


def create_simple_question(
    *,
    form: SurveyForm,
    question_name: str,
    question_type,
    question_title: Optional[str] = None
) -> Question:

    question = Question(
        survey=form,
        name=question_name,
        type=Question.QuestionType[question_type.upper()],
        title=question_title,
    )
    question.full_clean()
    question.save()
    return question


def create_image_question(
    *, form: SurveyForm, question_name: str, image_link: str
) -> Question:
    question = Question(
        survey=form,
        name=question_name,
        type=Question.QuestionType.IMAGE,
    )
    question.full_clean()
    question.save()

    question_option = QuestionOptions(
        question=question,
        type=QuestionOptions.OptionType.IMAGE,
        value=question_name,
        image_value=image_link,
    )
    question_option.full_clean()
    question_option.save()

    return question


def create_radiogroup_question(
    *,
    form: SurveyForm,
    question_name: str,
    question_title: Optional[str] = None,
    choices: list
) -> Question:
    question = Question(
        survey=form,
        name=question_name,
        type=Question.QuestionType.RADIOGROUP,
        title=question_title,
    )
    question.save()

    for choice in choices:
        if isinstance(choice, str):
            question_option = QuestionOptions(
                question=question,
                type=QuestionOptions.OptionType.TEXT,
                value=choice,
                text_value=choice,
            )

            question_option.full_clean()
            question_option.save()

        elif isinstance(choice, dict):
            choice_value = choice.get("value")
            choice_text = choice.get("text")

            question_option = QuestionOptions(
                question=question,
                type=QuestionOptions.OptionType.TEXT,
                value=choice_value,
                text_value=choice_text,
            )

            question_option.full_clean()
            question_option.save()

    return question


def create_questions(form: SurveyForm, pages: list):
    for page in pages:
        questions_elements = page.get("elements")
        for question_element in questions_elements:
            question_type = question_element.get("type")
            question_name = question_element.get("name")
            question_title = question_element.get("title", None)

            if question_type in [
                "text",
                "comment",
                "signaturepad",
                "expression",
                "html",
            ]:
                create_simple_question(
                    form=form,
                    question_name=question_name,
                    question_type=question_type,
                    question_title=question_title,
                )

            if question_type == "image":
                image_link = question_element.get("imageLink")
                create_image_question(
                    form=form, question_name=question_name, image_link=image_link
                )

            if question_type == "radiogroup":
                choices = question_element.get("choices")
                create_radiogroup_question(
                    form=form,
                    question_name=question_name,
                    question_title=question_title,
                    choices=choices,
                )
