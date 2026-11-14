// NumberField required menolak nol. Kehadiran price diperiksa saat create.
onRecordCreateRequest((e) => {
  const body = new DynamicModel({price: nullFloat()});
  try {
    e.bindBody(body);
  } catch (_) {
    throw new BadRequestError("price wajib berupa angka.", {
      price: new ValidationError("validation_invalid", "price wajib berupa angka."),
    });
  }
  if (body.price == null || !Number.isFinite(Number(body.price))) {
    throw new BadRequestError("price wajib berupa angka.", {
      price: new ValidationError("validation_required", "price wajib berupa angka."),
    });
  }
  return e.next();
}, "products");

onRecordUpdateRequest((e) => {
  const body = new DynamicModel({price: nullFloat()});
  try {
    e.bindBody(body);
  } catch (_) {
    throw new BadRequestError("price wajib berupa angka.", {
      price: new ValidationError("validation_invalid", "price wajib berupa angka."),
    });
  }
  if ("price" in e.requestInfo().body && body.price === null) {
    throw new BadRequestError("price wajib berupa angka.", {
      price: new ValidationError("validation_invalid", "price wajib berupa angka."),
    });
  }
  return e.next();
}, "products");
