from django.db import transaction

from .models import Question, QuestionOptions, SurveyForm, SurveyFormSettings


def survey_settings_activation(settings: SurveyFormSettings):
    form = settings.form
    parent_survey = form.parent

    with transaction.atomic():
        if settings.is_active:
            # غیرفعال کردن همه تنظیمات فرم ها با پدر یکسان
            SurveyFormSettings.objects.filter(form__parent=parent_survey).exclude(
                pk=settings.pk
            ).update(is_active=False)

            parent_survey.active_version = form
            parent_survey.save()

        else:
            if parent_survey.active_version == form:
                parent_survey.active_version = None
                parent_survey.save()


def create_question(
    *,
    form: SurveyForm,
    question_data: dict,
    parent_question: Question | None = None,
) -> Question:
    question_name = question_data.get("name")
    question_type = question_data.get("type")
    question_title = question_data.get("title", None)

    question = Question.objects.create(
        survey=form,
        name=question_name,
        type=Question.QuestionType[question_type.upper()],
        title=question_title,
        parent=parent_question,
    )

    handle_question_options(question=question, question_data=question_data)

    handle_nested_questions(
        form=form, parent_question=question, question_data=question_data
    )

    return question


def handle_question_options(*, question: Question, question_data: dict) -> None:
    question_type = question_data.get("type")

    if question_type in ["radiogroup", "ranking", "checkbox", "dropdown", "tagbox"]:
        choices = question_data.get("choices", [])

        if choices:
            for choice in choices:

                if isinstance(choice, str):
                    question_option = QuestionOptions(
                        question=question,
                        type=QuestionOptions.OptionType.TEXT,
                        value=choice,
                        text_value=choice,
                    )

                if isinstance(choice, dict):
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

    elif question_type == "boolean":
        choices = {
            "labelTrue": question_data.get("labelTrue", "Yes"),
            "labelFalse": question_data.get("labelFalse", "No"),
        }

        for label_value, boolean_value in choices.items():
            question_option = QuestionOptions(
                question=question,
                type=QuestionOptions.OptionType.BOOLEAN,
                value=label_value,
                boolean_value=True if label_value == "labelTrue" else False,
            )
            question_option.full_clean()
            question_option.save()

    elif question_type == "rating":
        choices = question_data.get("rateValues", None)
        rate_count = question_data.get("rateCount", None)

        if choices:
            for choice in choices:
                if isinstance(choice, dict):
                    question_option = QuestionOptions(
                        question=question,
                        type=QuestionOptions.OptionType.NUMERIC,
                        value=choice.get("text"),
                        numeric_value=choice.get("value"),
                    )
                    question_option.full_clean()
                    question_option.save()
                elif isinstance(choice, int):
                    question_option = QuestionOptions(
                        question=question,
                        type=QuestionOptions.OptionType.NUMERIC,
                        value=str(choice),
                        numeric_value=choice,
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

    elif question_type == "imagepicker":
        choices = question_data.get("choices", None)
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

    elif question_type in ["matrix", "matrixdropdown", "matrixdynamic"]:
        rows = question_data.get("rows", None)
        columns = question_data.get("columns", None)
        choices = question_data.get("choices", None)

        if rows:
            rows_question_option = QuestionOptions(
                question=question,
                type=QuestionOptions.OptionType.JSON,
                value="matrix_rows",
                json_value=rows,
            )
            rows_question_option.full_clean()
            rows_question_option.save()

        if choices:
            choices_question_option = QuestionOptions(
                question=question,
                type=QuestionOptions.OptionType.JSON,
                value="matrix_choices",
                json_value=choices,
            )
            choices_question_option.full_clean()
            choices_question_option.save()

        if columns:
            columns_question_option = QuestionOptions(
                question=question,
                type=QuestionOptions.OptionType.JSON,
                value="matrix_columns",
                json_value=columns,
            )
            columns_question_option.full_clean()
            columns_question_option.save()


def handle_nested_questions(
    *, form: SurveyForm, parent_question: Question, question_data: dict
) -> None:
    question_type = question_data.get("type")

    if question_type == "multipletext":
        nested_question_items = question_data.get("items")

        for nested_question_item in nested_question_items:
            nested_data = {
                "type": "text",
                "name": nested_question_item.get("name"),
                "title": nested_question_item.get("title", None),
            }
            create_question(
                form=form, question_data=nested_data, parent_question=parent_question
            )

    elif question_type in ["panel", "paneldynamic"]:
        nested_elements = question_data.get("elements") or question_data.get(
            "templateElements"
        )

        if nested_elements:

            for nested_element in nested_elements:
                create_question(
                    form=form,
                    question_data=nested_element,
                    parent_question=parent_question,
                )


def create_questions(*, form: SurveyForm, pages: list[dict]) -> None:
    for page in pages:
        questions_elements = page.get("elements")
        for question_element in questions_elements:
            create_question(
                form=form,
                question_data=question_element,
            )
