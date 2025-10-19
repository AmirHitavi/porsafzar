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


def create_question_with_text_options(
    *,
    form: SurveyForm,
    question_name: str,
    question_type: str,
    question_title: Optional[str] = None,
    choices: list[str | dict]
) -> Question:
    question = Question(
        survey=form,
        name=question_name,
        type=Question.QuestionType[question_type.upper()],
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


def create_boolean_question(
    *,
    form: SurveyForm,
    question_name: str,
    question_title: Optional[str] = None,
    choices: list
) -> Question:

    question = Question(
        survey=form,
        name=question_name,
        type=Question.QuestionType.BOOLEAN,
        title=question_title,
    )
    question.save()

    for label_value, boolean_value in choices.items():
        question_option = QuestionOptions(
            question=question,
            type=QuestionOptions.OptionType.BOOLEAN,
            value=label_value,
            boolean_value=True if label_value == "labelTrue" else False,
        )
        question_option.full_clean()
        question_option.save()

    return question


def create_rating_question(
    *,
    form: SurveyForm,
    question_name: str,
    question_title: Optional[str] = None,
    choices: Optional[list] = None,
    rate_count: Optional[int]
) -> Question:
    question = Question(
        survey=form,
        name=question_name,
        type=Question.QuestionType.RATING,
        title=question_title,
    )
    question.save()

    if choices:
        for choice in choices:
            question_option = QuestionOptions(
                question=question,
                type=QuestionOptions.OptionType.NUMERIC,
                value=choice.get("text"),
                numeric_value=choice.get("value"),
            )
            question_option.full_clean()
            question_option.save()
    elif rate_count:
        for i in range(1, rate_count + 1):
            question_option = QuestionOptions(
                question=question,
                type=QuestionOptions.OptionType.NUMERIC,
                value=str(i),
                numeric_value=i,
            )
            question_option.full_clean()
            question_option.save()
    return question


def create_questions(*, form: SurveyForm, pages: list[dict]) -> None:
    for page in pages:
        questions_elements = page.get("elements")
        for question_element in questions_elements:
            question_type = question_element.get("type")
            question_name = question_element.get("name")
            question_title = question_element.get("title", None)

            # radiogroup -> Done
            # rating -> Done
            # slider -> Done
            # checkbox -> Done
            # dropdown -> Done
            # tagbox -> Done
            # boolean -> Done
            # file -> Done
            # imagepicker
            # ranking -> Done
            # text -> Done
            # comment -> Done
            # multipletext
            # panel
            # paneldynamic
            # matrix
            # matrixdropdown
            # matrixdynamic
            # html -> Done
            # expression -> Done
            # image -> Done
            # signaturepad -> Done

            if question_type in [
                "text",
                "comment",
                "signaturepad",
                "expression",
                "html",
                "image",
                "slider",
                "file",
            ]:
                create_simple_question(
                    form=form,
                    question_name=question_name,
                    question_type=question_type,
                    question_title=question_title,
                )

            if question_type in [
                "radiogroup",
                "ranking",
                "checkbox",
                "dropdown",
                "tagbox",
            ]:
                choices = question_element.get("choices")
                create_question_with_text_options(
                    form=form,
                    question_name=question_name,
                    question_type=question_type,
                    question_title=question_title,
                    choices=choices,
                )

            if question_type == "boolean":

                choices = {
                    "labelTrue": question_element.get("labelTrue", "Yes"),
                    "labelFalse": question_element.get("labelFalse", "No"),
                }

                create_boolean_question(
                    form=form,
                    question_name=question_name,
                    question_title=question_title,
                    choices=choices,
                )

            if question_type == "rating":
                choices = question_element.get("rateValues", None)
                rate_count = question_element.get("rateCount", None)

                create_rating_question(
                    form=form,
                    question_name=question_name,
                    question_title=question_title,
                    choices=choices,
                    rate_count=rate_count,
                )
