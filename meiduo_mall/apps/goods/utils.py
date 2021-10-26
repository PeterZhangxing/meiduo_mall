

def get_breadcrumb(category):
    breadcrumb = {"cat1":"","cat2":"","cat3":""}

    if category.parent is None:
        breadcrumb['cat1'] = category
    elif category.subs.count() == 0:
        breadcrumb['cat3'] = category
        cat2 = category.parent
        breadcrumb['cat2'] = cat2
        breadcrumb['cat1'] = cat2.parent
    else:
        breadcrumb['cat2'] = category
        breadcrumb['cat1'] = category.parent

    return breadcrumb