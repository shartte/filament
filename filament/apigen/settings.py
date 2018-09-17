value_types = {
    "filament::Box",
    "filament::Frustum",
    "utils::Entity",
    "filament::LightManager::ShadowOptions",
    "filament::driver::FaceOffsets",
    "filament::Material::ParameterInfo",
    "filament::RenderableManager::Bone",
    "filament::View::DynamicResolutionOptions"
}

# We define certain value types as special "primitives" because we expect
# clients to use special platform types in their place.
record_to_primitive_map = {
    "filament::driver::SamplerParams": "SAMPLER_PARAMS",
    "math::details::TMat33<double>": "MAT33_DOUBLE",
    "math::details::TMat33<float>": "MAT33_FLOAT",
    "math::details::TMat44<double>": "MAT44_DOUBLE",
    "math::details::TMat44<float>": "MAT44_FLOAT",
    "math::details::TVec2<double>": "VEC2_DOUBLE",
    "math::details::TVec2<float>": "VEC2_FLOAT",
    "math::details::TVec3<double>": "VEC3_DOUBLE",
    "math::details::TVec3<float>": "VEC3_FLOAT",
    "math::details::TVec4<double>": "VEC4_DOUBLE",
    "math::details::TVec4<float>": "VEC4_FLOAT",
    "math::details::TQuaternion<float>": "QUATERNION_FLOAT"
}

# Sometimes a record type is given a special semantic via
# a typedef, such as float3 being aliased as LinearColor.
typedef_to_primitive_map = {
    "filament::LinearColor": "LINEAR_COLOR",
    "filament::LinearColorA": "LINEAR_COLOR_A"
}

# This superclass marks a class something that cannot be constructed or destructed by the client
# as such references to these objects are always borrowed and never owned
borrowed_obj_superclass = "filament::FilamentAPI"
builder_superclass = "filament::BuilderBase<T>"

interfaces = {
    "utils::EntityManager::Listener"
}

hidden_apis = {
    "filament::driver::ExternalContext"
}

public_apis = {
    "utils::EntityManager",
    "filament::Camera",
    "filament::Color",
    "filament::DebugRegistry",
    "filament::Fence",
    "filament::SwapChain",
    "filament::Engine",
    "filament::IndexBuffer",
    "filament::IndexBuffer::Builder",
    "filament::IndirectLight",
    "filament::IndirectLight::Builder",
    "filament::LightManager",
    "filament::LightManager::Builder",
    "filament::TextureSampler",
    "filament::MaterialInstance",
    "filament::Texture",
    "filament::Texture::Builder",
    "filament::Material",
    "filament::Material::Builder",
    "filament::VertexBuffer",
    "filament::VertexBuffer::Builder",
    "filament::Renderer",
    "filament::RenderableManager",
    "filament::RenderableManager::Builder",
    "filament::Scene",
    "filament::Skybox",
    "filament::Skybox::Builder",
    "filament::Stream",
    "filament::Stream::Builder",
    "filament::TransformManager",
    "filament::Viewport",
    "filament::View",
    "filament::driver::BufferDescriptor",
    "filament::driver::PixelBufferDescriptor"
}
