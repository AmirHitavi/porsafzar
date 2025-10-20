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
    question_title: Optional[str] = None,
    parent_question: Optional[Question] = None,
) -> Question:

    question = Question(
        survey=form,
        name=question_name,
        type=Question.QuestionType[question_type.upper()],
        title=question_title,
        parent=parent_question,
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
    choices: list[str | dict],
    parent_question: Optional[Question] = None,
) -> Question:
    question = Question(
        survey=form,
        name=question_name,
        type=Question.QuestionType[question_type.upper()],
        title=question_title,
        parent=parent_question,
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
    choices: list,
    question_title: Optional[str] = None,
    parent_question: Optional[Question] = None,
) -> Question:

    question = Question(
        survey=form,
        name=question_name,
        type=Question.QuestionType.BOOLEAN,
        title=question_title,
        parent=parent_question,
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
    rate_count: Optional[int],
    parent_question: Optional[Question] = None,
) -> Question:
    question = Question(
        survey=form,
        name=question_name,
        type=Question.QuestionType.RATING,
        title=question_title,
        parent=parent_question,
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


def create_image_picker_question(
    *,
    form: SurveyForm,
    question_name: str,
    question_title: Optional[str] = None,
    choices: list | None = None,
    parent_question: Optional[Question] = None,
) -> Question:
    question = Question(
        survey=form,
        name=question_name,
        type=Question.QuestionType.IMAGEPICKER,
        title=question_title,
        parent=parent_question,
    )
    question.save()

    if choices is not None:
        for choice in choices:
            question_option = QuestionOptions(
                question=question,
                type=QuestionOptions.OptionType.IMAGE,
                value=choice.get("value"),
                image_value=choice.get("imageLink"),
            )
            question_option.full_clean()
            question_option.save()

    return question


def create_multiple_text_question(
    *,
    form: SurveyForm,
    question_name: str,
    nested_question_items: list[dict],
    question_title: Optional[str] = None,
    parent_question: Optional[Question] = None,
) -> Question:
    question = Question(
        survey=form,
        name=question_name,
        type=Question.QuestionType.MULTIPLETEXT,
        title=question_title,
        parent=parent_question,
    )
    question.save()

    for nested_item in nested_question_items:
        nested_question_name = nested_item.get("name")
        nested_question_title = nested_item.get("title", None)

        nested_question = Question(
            survey=form,
            name=nested_question_name,
            type=Question.QuestionType.TEXT,
            title=nested_question_title,
            parent=question,
        )
        nested_question.save()

    return question


def create_nested_question(
    *, form: SurveyForm, question_element: dict, parent_question: Question
) -> Question:
    question_type = question_element.get("type")
    question_name = question_element.get("name")
    question_title = question_element.get("title", None)

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
        question = create_simple_question(
            form=form,
            question_name=question_name,
            question_type=question_type,
            question_title=question_title,
            parent_question=parent_question,
        )

    elif question_type in [
        "radiogroup",
        "ranking",
        "checkbox",
        "dropdown",
        "tagbox",
    ]:
        choices = question_element.get("choices")
        question = create_question_with_text_options(
            form=form,
            question_name=question_name,
            question_type=question_type,
            question_title=question_title,
            choices=choices,
            parent_question=parent_question,
        )
    elif question_type == "boolean":

        choices = {
            "labelTrue": question_element.get("labelTrue", "Yes"),
            "labelFalse": question_element.get("labelFalse", "No"),
        }

        question = create_boolean_question(
            form=form,
            question_name=question_name,
            question_title=question_title,
            choices=choices,
            parent_question=parent_question,
        )

    elif question_type == "rating":
        choices = question_element.get("rateValues", None)
        rate_count = question_element.get("rateCount", None)

        question = create_rating_question(
            form=form,
            question_name=question_name,
            question_title=question_title,
            choices=choices,
            rate_count=rate_count,
            parent_question=parent_question,
        )

    elif question_type == "imagepicker":
        choices = question_element.get("choices", None)

        question = create_image_picker_question(
            form=form,
            question_name=question_name,
            question_title=question_title,
            choices=choices,
            parent_question=parent_question,
        )

    elif question_type == "multipletext":
        nested_question_items = question_element.get("items")

        question = create_multiple_text_question(
            form=form,
            question_name=question_name,
            question_title=question_title,
            nested_question_items=nested_question_items,
            parent_question=parent_question,
        )

    elif question_type == "panel":
        nested_elements = question_element.get("elements")
        question = create_panel_question(
            form=form,
            question_name=question_name,
            question_type=question_type,
            question_title=question_title,
            nested_question_elements=nested_elements,
            parent_question=parent_question,
        )

    elif question_type == "paneldynamic":
        nested_elements = question_element.get("templateElements")
        question = create_panel_question(
            form=form,
            question_name=question_name,
            question_type=question_type,
            question_title=question_title,
            nested_question_elements=nested_elements,
        )

    return question


def create_panel_question(
    *,
    form: SurveyForm,
    question_name: str,
    question_type: str,
    question_title: Optional[str] = None,
    nested_question_elements: list[dict] | None = None,
    parent_question: Optional[Question] = None,
) -> Question:

    root_panel_question = Question(
        survey=form,
        name=question_name,
        type=Question.QuestionType[question_type.upper()],
        title=question_title,
        parent=parent_question,
    )
    root_panel_question.save()

    if nested_question_elements is not None:
        for nested_element in nested_question_elements:

            create_nested_question(
                form=form,
                question_element=nested_element,
                parent_question=root_panel_question,
            )

    return root_panel_question


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
            # imagepicker -> Done
            # ranking -> Done
            # text -> Done
            # comment -> Done
            # multipletext -> Done
            # panel -> Done
            # paneldynamic -> Done
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

            elif question_type in [
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

            elif question_type == "boolean":

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

            elif question_type == "rating":
                choices = question_element.get("rateValues", None)
                rate_count = question_element.get("rateCount", None)

                create_rating_question(
                    form=form,
                    question_name=question_name,
                    question_title=question_title,
                    choices=choices,
                    rate_count=rate_count,
                )

            elif question_type == "imagepicker":
                choices = question_element.get("choices", None)

                create_image_picker_question(
                    form=form,
                    question_name=question_name,
                    question_title=question_title,
                    choices=choices,
                )

            elif question_type == "multipletext":
                nested_question_items = question_element.get("items")

                create_multiple_text_question(
                    form=form,
                    question_name=question_name,
                    question_title=question_title,
                    nested_question_items=nested_question_items,
                )

            elif question_type == "panel":
                nested_elements = question_element.get("elements")
                create_panel_question(
                    form=form,
                    question_name=question_name,
                    question_type=question_type,
                    question_title=question_title,
                    nested_question_elements=nested_elements,
                )

            elif question_type == "paneldynamic":
                nested_elements = question_element.get("templateElements")
                create_panel_question(
                    form=form,
                    question_name=question_name,
                    question_type=question_type,
                    question_title=question_title,
                    nested_question_elements=nested_elements,
                )
